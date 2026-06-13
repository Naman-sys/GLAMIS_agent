from __future__ import annotations

import logging
from typing import Any
import httpx

from app.config.settings import get_settings

logger = logging.getLogger(__name__)


class AdminAPIClient:
    """Client for programmatically interacting with the GLAMIS Node.js backend."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = httpx.Client(base_url=self.settings.glamis_backend_url, timeout=30.0)
        self.access_token: str | None = None

    def _ensure_authenticated(self) -> None:
        """Log in to the GLAMIS Node.js backend if not already authenticated."""
        if self.access_token:
            return

        login_url = "/api/v1/users/login"
        payload = {
            "email": self.settings.glamis_admin_email,
            "password": self.settings.glamis_admin_password,
        }

        logger.info("Authenticating admin client with backend at %s...", self.settings.glamis_backend_url)
        try:
            response = self.client.post(login_url, json=payload)
            # Expecting 201 or 200
            if response.status_code not in (200, 201):
                logger.error("Failed to authenticate: HTTP %d, Response: %s", response.status_code, response.text)
                raise RuntimeError(f"Authentication failed with status code {response.status_code}")

            data = response.json()
            if not data.get("success"):
                raise RuntimeError(f"Authentication failed: {data.get('message', 'Unknown error')}")

            token = data.get("data", {}).get("accessToken")
            if not token:
                raise RuntimeError("No accessToken returned in login response")

            self.access_token = token
            # Set the header and cookie for subsequent requests
            self.client.headers.update({"Authorization": f"Bearer {token}"})
            self.client.cookies.set("accessToken", token)
            logger.info("Admin authentication successful.")
        except Exception as exc:
            logger.exception("Error during authentication with Node.js backend")
            raise RuntimeError(f"Failed to authenticate with Node.js backend: {exc}") from exc

    def create_interview(self, interview_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Create a new interview of specified type.
        
        Args:
            interview_type: One of 'company', 'subject', 'written', 'verbal', 'svar'
            payload: Type-specific JSON payload
            
        Returns:
            JSON response from backend e.g. {"message": "...", "link": "..."}
        """
        self._ensure_authenticated()
        
        # Normalize endpoint names (Svar is lowercase in URL)
        norm_type = interview_type.lower()
        url = f"/api/v1/admin/interview/{norm_type}/create"
        
        logger.info("Creating %s interview at %s...", interview_type, url)
        try:
            response = self.client.post(url, json=payload)
            if response.status_code not in (200, 201):
                logger.error("Create interview failed: HTTP %d, Response: %s", response.status_code, response.text)
                raise RuntimeError(f"Failed to create interview: {response.text}")
                
            return response.json()
        except Exception as exc:
            logger.exception("Error creating interview")
            raise RuntimeError(f"Failed to create interview via Node.js API: {exc}") from exc

    def fetch_interview_details(self, page: int = 1, limit: int = 50) -> list[dict[str, Any]]:
        """
        Fetch list of all scheduled interviews.
        
        Returns:
            List of interview detail dicts
        """
        self._ensure_authenticated()
        url = "/api/v1/admin/interview/fetchInterviewDetails"
        
        # We can pass pagination params in request body if needed, or query params.
        # Let's pass them as query params or json if needed.
        logger.info("Fetching interview details...")
        try:
            # Endpoint is POST
            response = self.client.post(url, json={"page": page, "limit": limit})
            if response.status_code not in (200, 201):
                logger.error("Fetch interview details failed: HTTP %d, Response: %s", response.status_code, response.text)
                return []
                
            data = response.json()
            # If standard API wrapper data.get("data") contains the list or list wrapper
            # Let's look at the response details: returns { interviews: [...] }
            # Wait, if it is wrapped in ApiResponse, it might be in data.get("data")
            raw_data = data.get("data", {})
            if isinstance(raw_data, dict):
                return raw_data.get("interviews", [])
            elif isinstance(raw_data, list):
                return raw_data
            return data.get("interviews", [])
        except Exception:
            logger.exception("Error fetching interview details")
            return []

    def fetch_status_counts(self) -> dict[str, int]:
        """
        Fetch status counts for interviews.
        """
        self._ensure_authenticated()
        url = "/api/v1/admin/interview/fetchInterviewStatusCount"
        try:
            response = self.client.post(url, json={})
            if response.status_code not in (200, 201):
                return {}
            data = response.json()
            raw_data = data.get("data", {})
            return raw_data if isinstance(raw_data, dict) else data
        except Exception:
            logger.exception("Error fetching status counts")
            return {}

    def download_attendance(self, interview_ids: list[str]) -> str:
        """
        Download attendance CSV for specified interview ID(s).
        
        Returns:
            Raw CSV text
        """
        self._ensure_authenticated()
        url = "/api/v1/admin/interview/downloadAttendance"
        
        # Build query parameters with multiple interviewId parameters
        params = [("interviewId", iid) for iid in interview_ids]
        
        logger.info("Downloading attendance for interview IDs: %s...", interview_ids)
        try:
            response = self.client.get(url, params=params)
            if response.status_code != 200:
                logger.error("Download attendance failed: HTTP %d, Response: %s", response.status_code, response.text)
                raise RuntimeError(f"Failed to download attendance: {response.text}")
                
            return response.text
        except Exception as exc:
            logger.exception("Error downloading attendance")
            raise RuntimeError(f"Failed to download attendance via Node.js API: {exc}") from exc
