"""Spaces and structures operations mixin (Portal API only)."""

import base64
import json
from typing import Any, Dict, List

from ..models import Space, Structure


class SpacesMixin:
    """
    Mixin providing space and structure operations via Portal API.

    Requires on self:
        - _request(method, endpoint, **kwargs) -> dict
        - auth_token (str)
        - get_objects_by_ids(ids) -> list
        - list_space_objects(space_id) -> list
    """

    def _get_user_id_from_token(self) -> str:
        """Extract user ID from JWT token."""
        token = self.auth_token
        if token.startswith("Bearer "):
            token = token[7:]

        # Decode JWT payload (middle part)
        payload = token.split(".")[1]
        # Add padding
        payload += "=" * (4 - len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload)
        data = json.loads(decoded)
        return data.get("id")

    def get_spaces(self) -> List[Space]:
        """
        Get all spaces the user has access to.

        Navigates: JWT → User → UserPersonal → Spaces

        Returns:
            List of Space instances
        """
        # 1. Get user ID from JWT
        user_id = self._get_user_id_from_token()
        if not user_id:
            return []

        # 2. Fetch User object to get userPersonalId
        user_data = self._request("POST", "/content/id-list", json={"ids": [user_id]})
        user_components = user_data.get("components", [])
        if not user_components:
            return []

        user_personal_id = user_components[0].get("data", {}).get("userPersonalId")
        if not user_personal_id:
            return []

        # 3. Fetch UserPersonal to get spaces list
        personal_data = self._request(
            "POST", "/content/id-list", json={"ids": [user_personal_id]}
        )
        personal_components = personal_data.get("components", [])
        if not personal_components:
            return []

        # 4. Extract space IDs from properties.spaces.val
        spaces_val = (
            personal_components[0]
            .get("properties", {})
            .get("spaces", {})
            .get("val", [])
        )
        space_ids = [s.get("id") for s in spaces_val if s.get("id")]

        if not space_ids:
            return []

        # 5. Fetch full space objects
        space_data = self._request("POST", "/content/id-list", json={"ids": space_ids})
        components = space_data.get("components", [])

        return [Space.from_dict(self._extract_space_info(c)) for c in components]

    def _extract_space_info(self, component: Dict[str, Any]) -> Dict[str, Any]:
        """Extract space info from a component object."""
        props = component.get("properties", {})
        return {
            "id": component.get("id"),
            "title": props.get("title", {}).get("val", "Untitled"),
            "createdAt": component.get("createdAt"),
            "updatedAt": component.get("lastUpdated"),
        }

    def get_space_info(self, space_id: str) -> Dict[str, Any]:
        """
        Get detailed space information including structures and collections.

        Args:
            space_id: Space UUID

        Returns:
            Dict with space details, structures, and collections
        """
        # Get all objects in the space
        elements = self._request(
            "POST", "/content/space-content", json={"spaceId": space_id}
        )
        element_ids = [e["id"] for e in elements.get("elements", [])]

        if not element_ids:
            return {"space": None, "structures": [], "collections": []}

        # Fetch all objects (in batches if needed)
        batch_size = 100
        all_components = []
        for i in range(0, len(element_ids), batch_size):
            batch = element_ids[i:i + batch_size]
            data = self._request("POST", "/content/id-list", json={"ids": batch})
            all_components.extend(data.get("components", []))

        # Categorize by type
        space_obj = None
        structures = []
        collections = []

        for comp in all_components:
            comp_type = comp.get("type", "")

            if comp.get("id") == space_id:
                space_obj = comp
            elif comp_type == "RootStructure":
                structures.append(self._extract_structure_info(comp))
            elif comp_type == "RootCollection":
                collections.append(self._extract_collection_info(comp))

        return {
            "space": space_obj,
            "structures": structures,
            "collections": collections,
        }

    def _extract_structure_info(self, component: Dict[str, Any]) -> Dict[str, Any]:
        """Extract structure info from a component object."""
        props = component.get("properties", {})
        return {
            "id": component.get("id"),
            "type": component.get("type"),
            "title": props.get("title", {}).get("val", ""),
            "pluralTitle": props.get("pluralTitle", {}).get("val", ""),
            "icon": props.get("icon", {}).get("val", ""),
        }

    def _extract_collection_info(self, component: Dict[str, Any]) -> Dict[str, Any]:
        """Extract collection info from a component object."""
        props = component.get("properties", {})
        return {
            "id": component.get("id"),
            "title": props.get("title", {}).get("val", ""),
            "structureId": props.get("structureId", {}).get("val", ""),
        }

    def get_structures(self, space_id: str) -> List[Structure]:
        """
        Get all structures (object types) in a space.

        Args:
            space_id: Space UUID

        Returns:
            List of Structure instances
        """
        info = self.get_space_info(space_id)
        return [Structure.from_dict(s) for s in info.get("structures", [])]

    def search_by_title_local(
        self, space_id: str, query: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search objects by title using local filtering.

        This fetches all objects and filters locally. For large spaces,
        consider using get_objects_by_ids with known IDs instead.

        Args:
            space_id: Space UUID
            query: Search query (case-insensitive substring match)
            limit: Maximum results to return

        Returns:
            List of matching object summaries with id, title, type
        """
        # Get all object IDs in space
        elements = self.list_space_objects(space_id)
        if not elements:
            return []

        element_ids = [e["id"] for e in elements]

        # Fetch all objects in batches
        batch_size = 100
        results = []
        query_lower = query.lower()

        for i in range(0, len(element_ids), batch_size):
            batch = element_ids[i:i + batch_size]
            data = self._request("POST", "/content/id-list", json={"ids": batch})

            for comp in data.get("components", []):
                props = comp.get("properties", {})
                title = props.get("title", {}).get("val", "")

                if query_lower in title.lower():
                    results.append({
                        "id": comp.get("id"),
                        "title": title,
                        "type": comp.get("type", ""),
                        "structureId": comp.get("structureId", ""),
                    })

                    if len(results) >= limit:
                        return results

        return results
