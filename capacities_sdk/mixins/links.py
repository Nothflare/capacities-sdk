"""Link operations mixin."""

from typing import Any, Dict, List

from ..exceptions import NotFoundError
from ..models import Object
from ..blocks import create_link_token, create_entity_block


class LinksMixin:
    """
    Mixin providing link operations.

    Requires on self:
        - _sync_entity(space_id, entity) -> dict
        - get_object(object_id) -> Object
        - get_objects_by_ids(object_ids) -> list
        - get_all_objects(space_id) -> list
    """

    def get_links(self, object_id: str) -> List[Dict[str, Any]]:
        """Get all links (references to other objects) from an object's content."""
        obj = self.get_object(object_id)
        if not obj:
            return []

        links = obj.get_links()
        return [
            {
                "id": link.id,
                "target_id": link.target_id,
                "target_structure_id": link.target_structure_id,
                "display_text": link.display_text,
                "type": link.type,
            }
            for link in links
        ]

    def get_backlinks(self, space_id: str, object_id: str) -> List[Object]:
        """Get all objects that link to a given object."""
        all_objects = self.get_all_objects(space_id)
        backlinks = []

        for obj in all_objects:
            if obj.id == object_id:
                continue

            linked_ids = obj.get_linked_object_ids()
            if object_id in linked_ids:
                backlinks.append(obj)

        return backlinks

    def add_link(
        self,
        space_id: str,
        source_object_id: str,
        target_object_id: str,
        display_text: str = None,
        as_block: bool = False,
    ) -> Object:
        """
        Add a link from one object to another.

        Creates either an inline LinkToken or an EntityBlock in the source
        object's content that references the target object.
        """
        import uuid as uuid_module
        from datetime import datetime, timezone

        source = self.get_object(source_object_id)
        if not source:
            raise NotFoundError(f"Source object not found: {source_object_id}")

        target = self.get_object(target_object_id)
        if not target:
            raise NotFoundError(f"Target object not found: {target_object_id}")

        entity = source.raw_data.copy()
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        entity["lastUpdated"] = now

        blocks_data = entity.get("data", {}).get("blocks", {})
        content_property_id = None

        for prop_id, block_list in blocks_data.items():
            if block_list:
                content_property_id = prop_id
                break

        if not content_property_id:
            content_property_id = str(uuid_module.uuid4())
            entity["properties"][content_property_id] = {"val": content_property_id}
            entity["data"]["blocks"][content_property_id] = []

        if as_block:
            entity_block = create_entity_block(
                target_id=target_object_id,
                target_structure_id=target.structure_id,
            )
            entity["data"]["blocks"][content_property_id].append(entity_block)
        else:
            link_text = display_text or target.title
            link_token = create_link_token(
                target_id=target_object_id,
                display_text=link_text,
                target_structure_id=target.structure_id,
            )

            blocks = entity["data"]["blocks"][content_property_id]
            text_block = None

            for block in reversed(blocks):
                if block.get("type") == "TextBlock":
                    text_block = block
                    break

            if text_block:
                if not text_block.get("tokens"):
                    text_block["tokens"] = []
                if text_block["tokens"]:
                    text_block["tokens"].append({
                        "type": "TextToken",
                        "id": str(uuid_module.uuid4()),
                        "text": " ",
                        "style": {"bold": False, "italic": False}
                    })
                text_block["tokens"].append(link_token)
            else:
                new_block = {
                    "id": str(uuid_module.uuid4()),
                    "type": "TextBlock",
                    "blocks": [],
                    "hierarchy": {"key": "Base", "val": 0},
                    "tokens": [link_token]
                }
                entity["data"]["blocks"][content_property_id].append(new_block)

        result = self._sync_entity(space_id, entity)
        return self.get_object(result["id"])

    def get_linked_objects(self, object_id: str) -> List[Object]:
        """Get all objects that a given object links to."""
        obj = self.get_object(object_id)
        if not obj:
            return []

        linked_ids = obj.get_linked_object_ids()
        if not linked_ids:
            return []

        return self.get_objects_by_ids(linked_ids)
