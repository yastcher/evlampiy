import asyncio
import base64
import http
import logging

import httpx

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"
OBSIDIAN_DEFAULT_REPO_NAME = "obsidian-notes"
OBSIDIAN_NOTES_FOLDER = "income"
MAX_RETRIES = 3


def _github_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }


async def get_github_username(token: str) -> str | None:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{GITHUB_API_BASE}/user", headers=_github_headers(token))
        if response.status_code == http.HTTPStatus.OK:
            return response.json()["login"]
        logger.error("Failed to get GitHub username, status: %s", response.status_code)
        return None


async def get_or_create_obsidian_repo(
    token: str, repo_name: str = OBSIDIAN_DEFAULT_REPO_NAME
) -> dict | None:
    username = await get_github_username(token)
    if not username:
        return None

    headers = _github_headers(token)

    async with httpx.AsyncClient() as client:
        # Check if repo exists
        response = await client.get(
            f"{GITHUB_API_BASE}/repos/{username}/{repo_name}",
            headers=headers,
        )
        if response.status_code == http.HTTPStatus.OK:
            logger.info("Repo %s/%s already exists", username, repo_name)
            return {"owner": username, "repo": repo_name, "token": token}

        if response.status_code != http.HTTPStatus.NOT_FOUND:
            logger.error("Failed to check repo, status: %s", response.status_code)
            return None

        # Create private repo
        create_response = await client.post(
            f"{GITHUB_API_BASE}/user/repos",
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

        # Create income/ folder via .gitkeep
        gitkeep_content = base64.b64encode(b"").decode("utf-8")
        await client.put(
            f"{GITHUB_API_BASE}/repos/{username}/{repo_name}/contents/{OBSIDIAN_NOTES_FOLDER}/.gitkeep",
            headers=headers,
            json={"message": "Init income folder", "content": gitkeep_content},
        )

    return {"owner": username, "repo": repo_name, "token": token}


async def put_github_file(
    token: str, owner: str, repo: str, path: str, content: str, commit_message: str
) -> bool:
    content_base64 = base64.b64encode(content.encode("utf-8")).decode("utf-8")
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{path}"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    url,
                    headers=_github_headers(token),
                    json={"message": commit_message, "content": content_base64},
                )
            if response.status_code in (http.HTTPStatus.OK, http.HTTPStatus.CREATED):
                return True
            if response.status_code == http.HTTPStatus.UNAUTHORIZED:
                logger.error("GitHub token is invalid or expired")
                return False
            logger.error("GitHub API error on attempt %s: status %s", attempt, response.status_code)
        except httpx.HTTPError as exc:
            logger.error("GitHub API network error on attempt %s: %s", attempt, exc)

        if attempt < MAX_RETRIES:
            await asyncio.sleep(2**attempt)

    return False


async def get_repo_contents(token: str, owner: str, repo: str, path: str = "") -> list[dict]:
    """Get list of files/folders in a repository path."""
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{path}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=_github_headers(token))
        if response.status_code == http.HTTPStatus.OK:
            data = response.json()
            if isinstance(data, list):
                return data
            return [data]
        logger.error("Failed to get repo contents, status: %s", response.status_code)
        return []


async def get_github_file(token: str, owner: str, repo: str, path: str) -> tuple[str, str] | None:
    """Get file content and SHA. Returns (content, sha) or None."""
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{path}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=_github_headers(token))
        if response.status_code == http.HTTPStatus.OK:
            data = response.json()
            content = base64.b64decode(data["content"]).decode("utf-8")
            return content, data["sha"]
        logger.error("Failed to get file, status: %s", response.status_code)
        return None


async def delete_github_file(
    token: str, owner: str, repo: str, path: str, sha: str, commit_message: str
) -> bool:
    """Delete a file from GitHub repository."""
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{path}"
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            url,
            headers=_github_headers(token),
            json={"message": commit_message, "sha": sha},
        )
        if response.status_code == http.HTTPStatus.OK:
            return True
        logger.error("Failed to delete file, status: %s", response.status_code)
        return False
