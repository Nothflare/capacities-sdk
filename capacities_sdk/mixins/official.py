"""Official (Public) API operations mixin."""

from typing import Any, Dict, List

from ..models import Space, Structure


class OfficialAPIMixin:
    """
    Mixin providing official/public API operations.

    Requires on self:
        - _request(method, endpoint, **kwargs) -> dict
    """

    def get_spaces(self) -> List[Space]:
        """Get all spaces (uses official API)."""
        data = self._request("GET", "/spaces", use_public_api=True)
        spaces = data.get("spaces", [])
        return [Space.from_dict(s) for s in spaces]

    def get_space_info(self, space_id: str) -> Dict[str, Any]:
        """Get space structures and collections (uses official API)."""
        data = self._request(
            "GET", "/space-info", params={"spaceid": space_id}, use_public_api=True
        )
        return data

    def get_structures(self, space_id: str) -> List[Structure]:
        """Get all structures (object types) in a space."""
        data = self.get_space_info(space_id)
        structures = data.get("structures", [])
        return [Structure.from_dict(s) for s in structures]

    def lookup(self, space_id: str, search_term: str) -> List[Dict[str, Any]]:
        """Lookup content by title (uses official API)."""
        data = self._request(
            "POST",
            "/lookup",
            json={"spaceId": space_id, "searchTerm": search_term},
            use_public_api=True,
        )
        return data.get("results", [])

    def save_weblink(
        self,
        space_id: str,
        url: str,
        title: str = None,
        description: str = None,
        tags: List[str] = None,
        md_text: str = None,
    ) -> Dict[str, Any]:
        """Save a weblink to a space (uses official API)."""
        payload = {"spaceId": space_id, "url": url}
        if title:
            payload["titleOverwrite"] = title
        if description:
            payload["descriptionOverwrite"] = description
        if tags:
            payload["tags"] = tags
        if md_text:
            payload["mdText"] = md_text

        return self._request("POST", "/save-weblink", json=payload, use_public_api=True)

    def save_to_daily_note(
        self,
        space_id: str,
        md_text: str,
        no_timestamp: bool = False,
    ) -> None:
        """Add text to today's daily note (uses official API)."""
        payload = {"spaceId": space_id, "mdText": md_text}
        if no_timestamp:
            payload["noTimeStamp"] = True

        self._request("POST", "/save-to-daily-note", json=payload, use_public_api=True)
