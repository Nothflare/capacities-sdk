"""Main client for Capacities API."""

from typing import Any, Dict, List
from urllib.parse import urljoin

import requests

from .exceptions import (
    AuthenticationError,
    CapacitiesError,
    NotFoundError,
    RateLimitError,
    SyncError,
    ValidationError,
)
from .models import Object
from .mixins import (
    ObjectsMixin,
    TasksMixin,
    LinksMixin,
    CollectionsMixin,
    BulkMixin,
    ExportMixin,
    GraphMixin,
    OfficialAPIMixin,
)


class CapacitiesClient(
    ObjectsMixin,
    TasksMixin,
    LinksMixin,
    CollectionsMixin,
    BulkMixin,
    ExportMixin,
    GraphMixin,
    OfficialAPIMixin,
):
    """
    Client for Capacities internal Portal API.

    This client provides full CRUD access to Capacities data via the
    internal Portal API used by the web app.

    Args:
        auth_token: JWT authentication token (from web app session or API settings)
        app_version: App version string (default: "web-1.57")
        base_url: Portal API base URL
        timeout: Request timeout in seconds
    """

    PORTAL_BASE_URL = "https://portal.capacities.io"
    PUBLIC_API_BASE_URL = "https://api.capacities.io"

    def __init__(
        self,
        auth_token: str,
        app_version: str = "web-1.57",
        base_url: str = None,
        timeout: int = 30,
    ):
        self.auth_token = auth_token
        self.app_version = app_version
        self.base_url = base_url or self.PORTAL_BASE_URL
        self.timeout = timeout
        self._session = requests.Session()
        self._setup_session()

    def _setup_session(self):
        """Configure session headers."""
        token = self.auth_token
        if not token.startswith("Bearer "):
            token = f"Bearer {token}"

        self._session.headers.update(
            {
                "auth-token": token,
                "appversion": self.app_version,
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Dict[str, Any] = None,
        json: Dict[str, Any] = None,
        use_public_api: bool = False,
    ) -> Dict[str, Any]:
        """Make an API request."""
        base = self.PUBLIC_API_BASE_URL if use_public_api else self.base_url
        url = urljoin(base + "/", endpoint.lstrip("/"))

        headers = {}
        if use_public_api:
            headers["Authorization"] = self._session.headers.get("auth-token", "")

        try:
            response = self._session.request(
                method=method,
                url=url,
                params=params,
                json=json,
                timeout=self.timeout,
                headers=headers if use_public_api else None,
            )
        except requests.RequestException as e:
            raise CapacitiesError(f"Request failed: {e}")

        if response.status_code == 401:
            raise AuthenticationError("Invalid or expired authentication token")
        elif response.status_code == 404:
            raise NotFoundError(f"Resource not found: {endpoint}")
        elif response.status_code == 429:
            retry_after = int(response.headers.get("RateLimit-Reset", 60))
            raise RateLimitError(
                f"Rate limit exceeded. Retry after {retry_after}s",
                retry_after=retry_after,
            )
        elif response.status_code >= 400:
            try:
                error_data = response.json()
                error_msg = error_data.get("error", response.text)
            except Exception:
                error_msg = response.text
            if "inputValidationFailed" in str(error_msg):
                raise ValidationError(f"Input validation failed: {error_msg}")
            raise CapacitiesError(
                f"API error: {error_msg}", status_code=response.status_code
            )

        if response.text:
            try:
                return response.json()
            except Exception:
                return {"raw": response.text}
        return {}

    # =========================================================================
    # Sync Operations (Core methods used by mixins)
    # =========================================================================

    def _get_sync_client_id(self) -> str:
        """Get or generate a sync client ID."""
        import uuid
        if not hasattr(self, "_sync_client_id"):
            self._sync_client_id = str(uuid.uuid4())
        return self._sync_client_id

    def _sync_entity(
        self, space_id: str, entity: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Sync an entity to the server.

        Args:
            space_id: Space UUID
            entity: Full entity dict

        Returns:
            Sync result with status
        """
        payload = {
            "syncClientId": self._get_sync_client_id(),
            "elements": [
                {
                    "spaceId": space_id,
                    "content": entity,
                }
            ],
        }

        data = self._request("POST", "/content/syncing", json=payload)

        results = data.get("componentReturnObjects", [])
        if results and results[0].get("status") == "success":
            return {
                "success": True,
                "id": results[0].get("id"),
                "syncTime": results[0].get("syncTime"),
            }
        else:
            raise SyncError(f"Sync failed: {data}")

    # =========================================================================
    # Full-Text Search
    # =========================================================================

    def search_content(
        self,
        space_id: str,
        query: str,
        limit: int = 50,
    ) -> List[Object]:
        """
        Full-text search across all content in a space.

        Searches object content, not just titles. More powerful than lookup.
        """
        try:
            data = self._request(
                "POST",
                "/resources/search",
                json={
                    "spaceId": space_id,
                    "query": query,
                    "limit": limit,
                }
            )

            results = data.get("results", data.get("items", []))
            if not results:
                return []

            if isinstance(results[0], dict):
                object_ids = [r.get("id", r.get("entityId")) for r in results]
            else:
                object_ids = results

            object_ids = [oid for oid in object_ids if oid][:limit]

            if not object_ids:
                return []

            return self.get_objects_by_ids(object_ids)

        except CapacitiesError:
            return self._search_content_fallback(space_id, query, limit)

    def _search_content_fallback(
        self, space_id: str, query: str, limit: int
    ) -> List[Object]:
        """Fallback content search by fetching all objects and searching locally."""
        query_lower = query.lower()
        all_objects = self.get_all_objects(space_id)
        matches = []

        for obj in all_objects:
            if query_lower in obj.title.lower():
                matches.append(obj)
                continue

            if obj.description and query_lower in obj.description.lower():
                matches.append(obj)
                continue

            content = obj.get_content_text()
            if content and query_lower in content.lower():
                matches.append(obj)
                continue

            if len(matches) >= limit:
                break

        return matches[:limit]
