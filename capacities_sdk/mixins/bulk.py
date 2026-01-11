"""Bulk operations mixin."""

import time
from typing import Any, Dict, List

from ..models import Object
from ..blocks import markdown_to_blocks


class BulkMixin:
    """
    Mixin providing bulk operations.

    Requires on self:
        - _request(method, endpoint, **kwargs) -> dict
        - _get_sync_client_id() -> str
        - get_objects_by_ids(object_ids) -> list
    """

    def _sync_entities(
        self, space_id: str, entities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Sync multiple entities to the server in a single request."""
        if not entities:
            return []

        payload = {
            "syncClientId": self._get_sync_client_id(),
            "elements": [
                {
                    "spaceId": space_id,
                    "content": entity,
                }
                for entity in entities
            ],
        }

        data = self._request("POST", "/content/syncing", json=payload)

        results = data.get("componentReturnObjects", [])
        return results

    def bulk_create(
        self,
        space_id: str,
        objects: List[Dict[str, Any]],
        batch_size: int = 50,
    ) -> List[Object]:
        """
        Create multiple objects in bulk.

        Args:
            space_id: Space UUID
            objects: List of object specs with keys: structure_id, title, content (optional),
                     description (optional), tags (optional)
            batch_size: Number of objects per batch (default 50)
        """
        import uuid
        from datetime import datetime, timezone

        all_created_ids = []

        for batch_start in range(0, len(objects), batch_size):
            batch = objects[batch_start:batch_start + batch_size]
            entities = []

            for obj_spec in batch:
                object_id = str(uuid.uuid4())
                now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

                obj_properties = {
                    "title": {"val": obj_spec["title"]},
                    "description": {"val": obj_spec.get("description", "")},
                    "icon": {},
                    "tags": {"val": obj_spec.get("tags", [])},
                }

                content_property_id = str(uuid.uuid4())
                blocks = {}
                if obj_spec.get("content"):
                    parsed_blocks = markdown_to_blocks(obj_spec["content"])
                    if parsed_blocks:
                        blocks[content_property_id] = parsed_blocks
                        obj_properties[content_property_id] = {"val": content_property_id}

                entity = {
                    "id": object_id,
                    "type": "RootEntity",
                    "structureId": obj_spec["structure_id"],
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
                entities.append(entity)

            results = self._sync_entities(space_id, entities)
            for result in results:
                if result.get("status") == "success":
                    all_created_ids.append(result.get("id"))

            if batch_start + batch_size < len(objects):
                time.sleep(0.1)

        return self.get_objects_by_ids(all_created_ids)

    def bulk_update(
        self,
        space_id: str,
        updates: List[Dict[str, Any]],
        batch_size: int = 50,
    ) -> List[Object]:
        """
        Update multiple objects in bulk.

        Args:
            space_id: Space UUID
            updates: List of update specs with keys: object_id, and optional:
                     title, content, description, tags
            batch_size: Number of objects per batch (default 50)
        """
        import uuid as uuid_module
        from datetime import datetime, timezone

        all_updated_ids = []

        for batch_start in range(0, len(updates), batch_size):
            batch = updates[batch_start:batch_start + batch_size]

            object_ids = [u["object_id"] for u in batch]
            current_objects = self.get_objects_by_ids(object_ids)
            obj_map = {obj.id: obj for obj in current_objects}

            entities = []
            for update_spec in batch:
                obj_id = update_spec["object_id"]
                obj = obj_map.get(obj_id)
                if not obj:
                    continue

                entity = obj.raw_data.copy()
                now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                entity["lastUpdated"] = now

                if "title" in update_spec:
                    entity["properties"]["title"] = {"val": update_spec["title"]}
                if "description" in update_spec:
                    entity["properties"]["description"] = {"val": update_spec["description"]}
                if "tags" in update_spec:
                    entity["properties"]["tags"] = {"val": update_spec["tags"]}

                if "content" in update_spec:
                    content_property_id = None
                    for prop_id, blocks in entity.get("data", {}).get("blocks", {}).items():
                        if blocks:
                            content_property_id = prop_id
                            break

                    if not content_property_id:
                        content_property_id = str(uuid_module.uuid4())
                        entity["properties"][content_property_id] = {"val": content_property_id}

                    parsed_blocks = markdown_to_blocks(update_spec["content"])
                    entity["data"]["blocks"][content_property_id] = parsed_blocks

                entities.append(entity)

            results = self._sync_entities(space_id, entities)
            for result in results:
                if result.get("status") == "success":
                    all_updated_ids.append(result.get("id"))

            if batch_start + batch_size < len(updates):
                time.sleep(0.1)

        return self.get_objects_by_ids(all_updated_ids)

    def bulk_delete(
        self,
        space_id: str,
        object_ids: List[str],
        batch_size: int = 50,
    ) -> Dict[str, Any]:
        """Delete multiple objects in bulk (moves to trash)."""
        from datetime import datetime, timezone

        success_count = 0
        failed_ids = []

        for batch_start in range(0, len(object_ids), batch_size):
            batch_ids = object_ids[batch_start:batch_start + batch_size]

            current_objects = self.get_objects_by_ids(batch_ids)
            obj_map = {obj.id: obj for obj in current_objects}

            entities = []
            batch_obj_ids = []
            for obj_id in batch_ids:
                obj = obj_map.get(obj_id)
                if not obj:
                    failed_ids.append(obj_id)
                    continue

                entity = obj.raw_data.copy()
                now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                entity["lastUpdated"] = now
                entity["deleteRequested"] = True
                entities.append(entity)
                batch_obj_ids.append(obj_id)

            if entities:
                results = self._sync_entities(space_id, entities)
                for i, result in enumerate(results):
                    if result.get("status") == "success":
                        success_count += 1
                    else:
                        if i < len(batch_obj_ids):
                            failed_ids.append(batch_obj_ids[i])

            if batch_start + batch_size < len(object_ids):
                time.sleep(0.1)

        return {
            "success_count": success_count,
            "failed_count": len(failed_ids),
            "failed_ids": failed_ids,
        }

    def bulk_restore(
        self,
        space_id: str,
        object_ids: List[str],
        batch_size: int = 50,
    ) -> List[Object]:
        """Restore multiple deleted objects from trash in bulk."""
        from datetime import datetime, timezone

        restored_ids = []

        for batch_start in range(0, len(object_ids), batch_size):
            batch_ids = object_ids[batch_start:batch_start + batch_size]

            current_objects = self.get_objects_by_ids(batch_ids)

            entities = []
            for obj in current_objects:
                entity = obj.raw_data.copy()
                now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                entity["lastUpdated"] = now
                entity["deleteRequested"] = False
                entities.append(entity)

            if entities:
                results = self._sync_entities(space_id, entities)
                for result in results:
                    if result.get("status") == "success":
                        restored_ids.append(result.get("id"))

            if batch_start + batch_size < len(object_ids):
                time.sleep(0.1)

        return self.get_objects_by_ids(restored_ids)

    def clone_objects(
        self,
        space_id: str,
        object_ids: List[str],
        title_prefix: str = "Copy of ",
    ) -> List[Object]:
        """Clone existing objects with new IDs."""
        import uuid as uuid_module
        from datetime import datetime, timezone

        objects = self.get_objects_by_ids(object_ids)
        if not objects:
            return []

        entities = []
        for obj in objects:
            entity = obj.raw_data.copy()
            entity["id"] = str(uuid_module.uuid4())
            now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            entity["createdAt"] = now
            entity["lastUpdated"] = now
            entity["deleteRequested"] = False

            old_title = entity.get("properties", {}).get("title", {}).get("val", "")
            entity["properties"]["title"] = {"val": f"{title_prefix}{old_title}"}

            entity["policies"] = [
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
            ]

            entities.append(entity)

        results = self._sync_entities(space_id, entities)
        created_ids = [
            r.get("id") for r in results
            if r.get("status") == "success"
        ]

        return self.get_objects_by_ids(created_ids)
