"""Collection operations mixin."""

from typing import List

from ..exceptions import NotFoundError
from ..models import Object


class CollectionsMixin:
    """
    Mixin providing collection (database) operations.

    Requires on self:
        - _sync_entity(space_id, entity) -> dict
        - get_object(object_id) -> Object
        - get_all_objects(space_id) -> list
    """

    def add_to_collection(
        self, space_id: str, object_id: str, collection_id: str
    ) -> Object:
        """Add an object to a collection (database)."""
        import uuid
        from datetime import datetime, timezone

        obj = self.get_object(object_id)
        if not obj:
            raise NotFoundError(f"Object not found: {object_id}")

        entity = obj.raw_data.copy()
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        entity["lastUpdated"] = now

        databases = entity.get("databases", [])
        for db in databases:
            if db.get("id") == collection_id:
                return obj

        link_id = str(uuid.uuid4())
        databases.append({
            "id": collection_id,
            "link": {
                "id": link_id,
                "type": "Database",
                "createdAt": now,
                "data": {"toStructureId": "RootDatabase"},
                "policies": []
            }
        })
        entity["databases"] = databases

        result = self._sync_entity(space_id, entity)
        return self.get_object(result["id"])

    def remove_from_collection(
        self, space_id: str, object_id: str, collection_id: str
    ) -> Object:
        """Remove an object from a collection (database)."""
        from datetime import datetime, timezone

        obj = self.get_object(object_id)
        if not obj:
            raise NotFoundError(f"Object not found: {object_id}")

        entity = obj.raw_data.copy()
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        entity["lastUpdated"] = now

        databases = entity.get("databases", [])
        entity["databases"] = [db for db in databases if db.get("id") != collection_id]

        result = self._sync_entity(space_id, entity)
        return self.get_object(result["id"])

    def get_object_collections(self, object_id: str) -> List[str]:
        """Get list of collection IDs an object belongs to."""
        obj = self.get_object(object_id)
        if not obj:
            return []

        databases = obj.raw_data.get("databases", [])
        return [db.get("id") for db in databases if db.get("id")]

    def get_collection_objects(
        self, space_id: str, collection_id: str
    ) -> List[Object]:
        """Get all objects in a collection."""
        all_objects = self.get_all_objects(space_id)
        return [
            obj for obj in all_objects
            if collection_id in [
                db.get("id") for db in obj.raw_data.get("databases", [])
            ]
        ]
