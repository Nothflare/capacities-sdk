"""Object CRUD operations mixin."""

import time
from typing import Any, Dict, List, Optional

from ..exceptions import NotFoundError
from ..models import Object
from ..blocks import markdown_to_blocks


class ObjectsMixin:
    """
    Mixin providing object CRUD operations.

    Requires on self:
        - _request(method, endpoint, **kwargs) -> dict
        - _sync_entity(space_id, entity) -> dict
        - lookup(space_id, search_term) -> list (for search_by_title)
    """

    # =========================================================================
    # READ Operations
    # =========================================================================

    def get_objects_by_ids(self, object_ids: List[str]) -> List[Object]:
        """
        Get full objects by their IDs.

        Args:
            object_ids: List of object UUIDs

        Returns:
            List of Object instances with full content
        """
        if not object_ids:
            return []

        data = self._request("POST", "/content/id-list", json={"ids": object_ids})
        components = data.get("components", [])
        return [Object.from_dict(c) for c in components]

    def get_object(self, object_id: str) -> Optional[Object]:
        """
        Get a single object by ID.

        Args:
            object_id: Object UUID

        Returns:
            Object instance or None if not found
        """
        objects = self.get_objects_by_ids([object_id])
        return objects[0] if objects else None

    def list_space_objects(self, space_id: str) -> List[Dict[str, Any]]:
        """
        List all objects in a space (IDs and last updated times).

        Args:
            space_id: Space UUID

        Returns:
            List of {id, lastUpdated} dicts
        """
        data = self._request("POST", "/content/space-content", json={"spaceId": space_id})
        return data.get("elements", [])

    def get_all_objects(
        self, space_id: str, batch_size: int = 50
    ) -> List[Object]:
        """
        Get all objects in a space with full content.

        Args:
            space_id: Space UUID
            batch_size: Number of objects to fetch per batch

        Returns:
            List of all Object instances in the space
        """
        # First get all IDs
        elements = self.list_space_objects(space_id)
        all_ids = [e["id"] for e in elements]

        # Fetch in batches
        all_objects = []
        for i in range(0, len(all_ids), batch_size):
            batch_ids = all_ids[i : i + batch_size]
            objects = self.get_objects_by_ids(batch_ids)
            all_objects.extend(objects)
            # Small delay to avoid rate limiting
            if i + batch_size < len(all_ids):
                time.sleep(0.1)

        return all_objects

    def get_objects_by_structure(
        self, space_id: str, structure_id: str
    ) -> List[Object]:
        """
        Get all objects of a specific type/structure.

        Args:
            space_id: Space UUID
            structure_id: Structure ID (e.g., 'RootPage', 'RootDailyNote', or custom UUID)

        Returns:
            List of Object instances matching the structure
        """
        all_objects = self.get_all_objects(space_id)
        return [obj for obj in all_objects if obj.structure_id == structure_id]

    # =========================================================================
    # Search
    # =========================================================================

    def search_by_title(self, space_id: str, query: str, limit: int = 50) -> List[Object]:
        """
        Search objects by title.

        Args:
            space_id: Space UUID
            query: Search query (case-insensitive substring match)
            limit: Maximum results to return

        Returns:
            List of matching Object instances
        """
        results = self.search_by_title_local(space_id, query, limit=limit)
        if not results:
            return []

        object_ids = [r["id"] for r in results]
        return self.get_objects_by_ids(object_ids)

    # =========================================================================
    # Trash Operations
    # =========================================================================

    def get_trash(
        self, space_id: str, last_updated: str = None
    ) -> List[Dict[str, Any]]:
        """
        Get deleted objects in trash.

        Args:
            space_id: Space UUID
            last_updated: Optional timestamp filter

        Returns:
            List of trashed items
        """
        params = {}
        if last_updated:
            params["lastUpdated"] = last_updated

        data = self._request(
            "GET", f"/content/trash/{space_id}", params=params if params else None
        )
        return data.get("items", data.get("elements", []))

    # =========================================================================
    # WRITE Operations
    # =========================================================================

    def create_object(
        self,
        space_id: str,
        structure_id: str,
        title: str,
        content: str = None,
        description: str = None,
        tags: List[str] = None,
        properties: Dict[str, Any] = None,
    ) -> Object:
        """
        Create a new object in a space.

        Content is automatically parsed from markdown format, supporting:
        - # Headings (levels 1-6)
        - ```language code blocks ```
        - - Bullet lists and 1. Numbered lists
        - --- Horizontal rules
        - > Blockquotes
        - **bold**, *italic* inline formatting

        Args:
            space_id: Space UUID
            structure_id: Structure ID (object type), e.g., UUID of a Note structure
            title: Object title
            content: Optional markdown content (auto-parsed into blocks)
            description: Optional description
            tags: Optional list of tag IDs
            properties: Optional additional custom properties

        Returns:
            Created Object instance
        """
        import uuid
        from datetime import datetime, timezone

        object_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        # Build properties
        obj_properties = {
            "title": {"val": title},
            "description": {"val": description} if description else {},
            "icon": {},
            "tags": {"val": tags or []},
        }

        # Add custom properties
        if properties:
            for key, value in properties.items():
                obj_properties[key] = {"val": value}

        # Build content blocks - auto-parse markdown
        content_property_id = str(uuid.uuid4())
        blocks = {}
        if content:
            # Parse markdown into blocks
            parsed_blocks = markdown_to_blocks(content)
            if parsed_blocks:
                blocks[content_property_id] = parsed_blocks
                # Reference the content property
                obj_properties[content_property_id] = {"val": content_property_id}

        # Build the full entity
        entity = {
            "id": object_id,
            "type": "RootEntity",
            "structureId": structure_id,
            "createdAt": now,
            "lastUpdated": now,
            "loadingState": "full",
            "deleteRequested": False,
            "properties": obj_properties,
            "data": {
                "blocks": blocks,
                "hidePropertySection": False,
            },
            "databases": [],
            "policies": [
                {
                    "name": "write",
                    "principals": [
                        {
                            "name": "SpaceEditor",
                            "config": {"spaceId": space_id},
                        }
                    ],
                    "principalType": "Role",
                }
            ],
            "linkNodes": [],
        }

        # Sync to server
        result = self._sync_entity(space_id, entity)

        # Fetch and return the created object
        return self.get_object(result["id"])

    def update_object(
        self,
        space_id: str,
        object_id: str,
        title: str = None,
        content: str = None,
        description: str = None,
        tags: List[str] = None,
        properties: Dict[str, Any] = None,
    ) -> Object:
        """
        Update an existing object.

        Content is automatically parsed from markdown format, supporting:
        - # Headings (levels 1-6)
        - ```language code blocks ```
        - - Bullet lists and 1. Numbered lists
        - --- Horizontal rules
        - > Blockquotes
        - **bold**, *italic* inline formatting

        Args:
            space_id: Space UUID
            object_id: Object UUID to update
            title: New title (optional)
            content: New markdown content (optional, replaces existing, auto-parsed)
            description: New description (optional)
            tags: New tags list (optional)
            properties: Additional properties to update (optional)

        Returns:
            Updated Object instance
        """
        import uuid
        from datetime import datetime, timezone

        # Get current object
        obj = self.get_object(object_id)
        if not obj:
            raise NotFoundError(f"Object not found: {object_id}")

        entity = obj.raw_data.copy()
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        entity["lastUpdated"] = now

        # Update properties
        if title is not None:
            entity["properties"]["title"] = {"val": title}
        if description is not None:
            entity["properties"]["description"] = {"val": description}
        if tags is not None:
            entity["properties"]["tags"] = {"val": tags}
        if properties:
            for key, value in properties.items():
                entity["properties"][key] = {"val": value}

        # Update content if provided - auto-parse markdown
        if content is not None:
            # Find or create content property
            content_property_id = None
            for prop_id, blocks in entity.get("data", {}).get("blocks", {}).items():
                if blocks:
                    content_property_id = prop_id
                    break

            if not content_property_id:
                content_property_id = str(uuid.uuid4())
                entity["properties"][content_property_id] = {"val": content_property_id}

            # Parse markdown into blocks
            parsed_blocks = markdown_to_blocks(content)
            entity["data"]["blocks"][content_property_id] = parsed_blocks

        # Sync to server
        result = self._sync_entity(space_id, entity)

        # Fetch and return the updated object
        return self.get_object(result["id"])

    def delete_object(self, space_id: str, object_id: str) -> bool:
        """
        Delete an object (moves to trash).

        Args:
            space_id: Space UUID
            object_id: Object UUID to delete

        Returns:
            True if deletion was successful
        """
        from datetime import datetime, timezone

        # Get current object
        obj = self.get_object(object_id)
        if not obj:
            raise NotFoundError(f"Object not found: {object_id}")

        entity = obj.raw_data.copy()
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        entity["lastUpdated"] = now
        entity["deleteRequested"] = True

        # Sync to server
        result = self._sync_entity(space_id, entity)
        return result.get("success", False)

    def restore_object(self, space_id: str, object_id: str) -> Object:
        """
        Restore a deleted object from trash.

        Args:
            space_id: Space UUID
            object_id: Object UUID to restore

        Returns:
            Restored Object instance
        """
        from datetime import datetime, timezone

        # Get current object (should have deleteRequested=True)
        obj = self.get_object(object_id)
        if not obj:
            raise NotFoundError(f"Object not found: {object_id}")

        entity = obj.raw_data.copy()
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        entity["lastUpdated"] = now
        entity["deleteRequested"] = False

        # Sync to server
        result = self._sync_entity(space_id, entity)

        # Fetch and return the restored object
        return self.get_object(result["id"])
