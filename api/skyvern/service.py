import httpx
from django.conf import settings

from skyvern.constants import SKYVERN_BASE_URL
from skyvern.exceptions import SkyvernError


class SkyvernService:
    @staticmethod
    def _get_headers() -> dict:
        return {
            "x-api-key": settings.SKYVERN_API_KEY,
            "Content-Type": "application/json",
        }

    @staticmethod
    def run_workflow(workflow_id: str, parameters: dict) -> str:
        try:
            response = httpx.post(
                f"{SKYVERN_BASE_URL}/v1/run/workflows",
                headers=SkyvernService._get_headers(),
                json={
                    "workflow_id": workflow_id,
                    "parameters": parameters,
                },
            )
            response.raise_for_status()
            return response.json()["run_id"]
        except Exception as e:
            raise SkyvernError(str(e))
