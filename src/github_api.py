import asyncio
import base64
import dataclasses
import http
import logging
import typing

import httpx

from src import const, obsidian_layout

logger = logging.getLogger(__name__)

OBSIDIAN_DEFAULT_REPO_NAME = "obsidian-notes"
MAX_RETRIES = 3
# How many of the user's repos to offer as inline buttons during the connect flow.
REPO_LIST_LIMIT = 20


@dataclasses.dataclass(frozen=True, slots=True)
class GitHubRepo:
    """GitHub repository credentials."""

    token: str
    owner: str
    repo: str


def _github_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }


async def get_github_username(token: str) -> str | None:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{const.GITHUB_API_BASE}/user", headers=_github_headers(token))
        if response.status_code == http.HTTPStatus.OK:
            return str(response.json()["login"])
        logger.error("Failed to get GitHub username, status: %s", response.status_code)
        return None


async def list_user_repos(token: str, limit: int = REPO_LIST_LIMIT) -> list[str]:
    """Return the user's own repo names, most-recently-updated first (capped at `limit`)."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{const.GITHUB_API_BASE}/user/repos",
            headers=_github_headers(token),
            params={"per_page": limit, "sort": "updated", "affiliation": "owner"},
        )
    if response.status_code != http.HTTPStatus.OK:
        logger.error("Failed to list repos, status: %s", response.status_code)
        return []
    return [str(item["name"]) for item in response.json()]


async def get_or_create_obsidian_repo(token: str, repo_name: str = OBSIDIAN_DEFAULT_REPO_NAME) -> GitHubRepo | None:
    username = await get_github_username(token)
    if not username:
        return None

    headers = _github_headers(token)

    async with httpx.AsyncClient() as client:
        # Check if repo exists
        response = await client.get(
            f"{const.GITHUB_API_BASE}/repos/{username}/{repo_name}",
            headers=headers,
        )
        if response.status_code == http.HTTPStatus.OK:
            logger.info("Repo %s/%s already exists", username, repo_name)
            return GitHubRepo(token=token, owner=username, repo=repo_name)

        if response.status_code != http.HTTPStatus.NOT_FOUND:
            logger.error("Failed to check repo, status: %s", response.status_code)
            return None

        # Create private repo
        create_response = await client.post(
            f"{const.GITHUB_API_BASE}/user/repos",
            headers=headers,
            json={"name": repo_name, "private": True, "auto_init": True},
        )
        if create_response.status_code not in (
            http.HTTPStatus.OK,
            http.HTTPStatus.CREATED,
        ):
            logger.error("Failed to create repo, status: %s", create_response.status_code)
            return None

        logger.info("Created repo %s/%s", username, repo_name)

        # Seed the bot's working folders (inbox + trash) so they always exist
        gitkeep_content = base64.b64encode(b"").decode("utf-8")
        for folder in (obsidian_layout.inbox_dir(), obsidian_layout.trash_dir()):
            await client.put(
                f"{const.GITHUB_API_BASE}/repos/{username}/{repo_name}/contents/{folder}/.gitkeep",
                headers=headers,
                json={"message": f"Init {folder} folder", "content": gitkeep_content},
            )

    return GitHubRepo(token=token, owner=username, repo=repo_name)


async def put_github_file(repo_info: GitHubRepo, path: str, content: str, commit_message: str) -> bool:
    content_base64 = base64.b64encode(content.encode("utf-8")).decode("utf-8")
    url = f"{const.GITHUB_API_BASE}/repos/{repo_info.owner}/{repo_info.repo}/contents/{path}"
    payload: dict[str, typing.Any] = {"message": commit_message, "content": content_base64}

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.put(url, headers=_github_headers(repo_info.token), json=payload)
            if response.status_code in (http.HTTPStatus.OK, http.HTTPStatus.CREATED):
                return True
            if response.status_code == http.HTTPStatus.UNAUTHORIZED:
                logger.error("GitHub token is invalid or expired")
                return False
            if response.status_code == http.HTTPStatus.UNPROCESSABLE_ENTITY:
                existing = await get_github_file(repo_info, path)
                if not existing:
                    logger.error("GitHub API: file exists at %s but SHA fetch failed", path)
                    return False
                payload["sha"] = existing[1]
                logger.debug("File already exists at %s, retrying with SHA", path)
                continue
            logger.error("GitHub API error on attempt %s: status %s", attempt, response.status_code)
        except httpx.HTTPError as exc:
            logger.error("GitHub API network error on attempt %s: %s", attempt, exc)

        if attempt < MAX_RETRIES:
            await asyncio.sleep(2**attempt)

    return False


async def get_repo_contents(repo_info: GitHubRepo, path: str = "") -> list[dict[str, typing.Any]]:
    """Get list of files/folders in a repository path."""
    url = f"{const.GITHUB_API_BASE}/repos/{repo_info.owner}/{repo_info.repo}/contents/{path}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=_github_headers(repo_info.token))
        if response.status_code == http.HTTPStatus.OK:
            data: list[dict[str, typing.Any]] | dict[str, typing.Any] = response.json()
            if isinstance(data, list):
                return data
            return [data]
        logger.error("Failed to get repo contents, status: %s", response.status_code)
        return []


async def get_github_file(repo_info: GitHubRepo, path: str) -> tuple[str, str] | None:
    """Get file content and SHA. Returns (content, sha) or None."""
    url = f"{const.GITHUB_API_BASE}/repos/{repo_info.owner}/{repo_info.repo}/contents/{path}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=_github_headers(repo_info.token))
        if response.status_code == http.HTTPStatus.OK:
            data: dict[str, typing.Any] = response.json()
            content = base64.b64decode(data["content"]).decode("utf-8")
            return content, str(data["sha"])
        if response.status_code == http.HTTPStatus.NOT_FOUND:
            logger.debug("File not found: %s", path)
        else:
            logger.error("Failed to get file, status: %s", response.status_code)
        return None


_OBSIDIAN_GIT_CONFIG_PATH = ".obsidian/plugins/obsidian-git/data.json"
_OBSIDIAN_GIT_CONFIG = """{
  "autoPullInterval": 10,
  "autoPullOnBoot": true,
  "pullBeforePush": true,
  "commitMessage": "vault backup: {{date}}",
  "syncMethod": "rebase"
}
"""


async def create_obsidian_git_config(repo_info: GitHubRepo) -> bool:
    """Create or update obsidian-git plugin config in the repo."""
    return await put_github_file(
        repo_info=repo_info,
        path=_OBSIDIAN_GIT_CONFIG_PATH,
        content=_OBSIDIAN_GIT_CONFIG,
        commit_message="Add obsidian-git config",
    )


async def delete_github_file(repo_info: GitHubRepo, path: str, sha: str, commit_message: str) -> bool:
    """Delete a file from GitHub repository."""
    url = f"{const.GITHUB_API_BASE}/repos/{repo_info.owner}/{repo_info.repo}/contents/{path}"
    async with httpx.AsyncClient() as client:
        response = await client.request(
            "DELETE",
            url,
            headers=_github_headers(repo_info.token),
            json={"message": commit_message, "sha": sha},
        )
        if response.status_code == http.HTTPStatus.OK:
            return True
        logger.error("Failed to delete file, status: %s", response.status_code)
        return False
