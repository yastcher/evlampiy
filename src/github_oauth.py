import asyncio
import logging

import httpx

from src.config import settings

logger = logging.getLogger(__name__)

GITHUB_DEVICE_CODE_URL = "https://github.com/login/device/code"
GITHUB_OAUTH_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_OAUTH_SCOPE = "repo"
GITHUB_OAUTH_GRANT_TYPE = "urn:ietf:params:oauth:grant-type:device_code"


async def get_github_device_code() -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            GITHUB_DEVICE_CODE_URL,
            data={"client_id": settings.github_client_id, "scope": GITHUB_OAUTH_SCOPE},
            headers={"Accept": "application/json"},
        )
        return response.json()


async def poll_github_for_token(device_code: str, interval: int, expires_in: int) -> str | None:
    elapsed = 0
    poll_interval = interval

    async with httpx.AsyncClient() as client:
        while elapsed < expires_in:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

            response = await client.post(
                GITHUB_OAUTH_TOKEN_URL,
                data={
                    "client_id": settings.github_client_id,
                    "device_code": device_code,
                    "grant_type": GITHUB_OAUTH_GRANT_TYPE,
                },
                headers={"Accept": "application/json"},
            )
            body = response.json()

            if "error" not in body:
                return body["access_token"]

            error = body["error"]
            if error == "authorization_pending":
                continue
            elif error == "slow_down":
                poll_interval += 5
                continue
            elif error in ("expired_token", "access_denied"):
                logger.info("GitHub OAuth stopped: %s", error)
                return None
            else:
                logger.error("GitHub OAuth unexpected error: %s", error)
                return None

    logger.info("GitHub OAuth polling timed out after %s seconds", expires_in)
    return None
