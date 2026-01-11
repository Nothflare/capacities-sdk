"""Export/Import operations mixin."""

import time
from typing import Any, Dict, List

from ..models import Object


class ExportMixin:
    """
    Mixin providing export/import operations.

    Requires on self:
        - get_all_objects(space_id) -> list
        - get_objects_by_ids(object_ids) -> list
        - get_structures(space_id) -> list
        - _sync_entities(space_id, entities) -> list
    """

    def export_space_json(
        self,
        space_id: str,
        include_content: bool = True,
    ) -> Dict[str, Any]:
        """
        Export all objects in a space to JSON format.

        Creates a complete backup that can be used for import.
        """
        from datetime import datetime, timezone

        objects = self.get_all_objects(space_id)

        exported_objects = []
        for obj in objects:
            if include_content:
                exported_objects.append(obj.raw_data)
            else:
                exported_objects.append({
                    "id": obj.id,
                    "structureId": obj.structure_id,
                    "properties": {
                        "title": {"val": obj.title},
                        "description": {"val": obj.description or ""},
                        "tags": {"val": obj.tags},
                    },
                    "createdAt": obj.raw_data.get("createdAt"),
                    "lastUpdated": obj.raw_data.get("lastUpdated"),
                })

        structure_info = []
        try:
            structures = self.get_structures(space_id)
            structure_info = [
                {
                    "id": s.id,
                    "title": s.title,
                    "pluralName": s.plural_name,
                }
                for s in structures
            ]
        except Exception:
            structure_ids = set(obj.structure_id for obj in objects)
            structure_info = [{"id": sid, "title": sid, "pluralName": sid} for sid in structure_ids]

        return {
            "version": "1.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "space_id": space_id,
            "object_count": len(exported_objects),
            "structures": structure_info,
            "objects": exported_objects,
        }

    def export_objects_to_markdown(
        self,
        space_id: str,
        object_ids: List[str] = None,
    ) -> List[Dict[str, Any]]:
        """Export objects as markdown files."""
        import re

        if object_ids:
            objects = self.get_objects_by_ids(object_ids)
        else:
            objects = self.get_all_objects(space_id)

        exports = []
        for obj in objects:
            safe_title = re.sub(r'[<>:"/\\|?*]', '_', obj.title)
            safe_title = safe_title[:100]
            filename = f"{safe_title}.md"

            md_lines = [f"# {obj.title}"]

            if obj.description:
                md_lines.append("")
                md_lines.append(f"> {obj.description}")

            md_lines.append("")
            md_lines.append("---")
            md_lines.append("")

            md_lines.append(f"<!-- ")
            md_lines.append(f"id: {obj.id}")
            md_lines.append(f"type: {obj.structure_id}")
            if obj.created_at:
                md_lines.append(f"created: {obj.created_at.isoformat()}")
            if obj.last_updated:
                md_lines.append(f"updated: {obj.last_updated.isoformat()}")
            if obj.tags:
                md_lines.append(f"tags: {', '.join(obj.tags)}")
            md_lines.append(" -->")
            md_lines.append("")

            content = obj.get_content_text()
            if content:
                md_lines.append(content)

            linked_ids = obj.get_linked_object_ids()
            if linked_ids:
                md_lines.append("")
                md_lines.append("## Links")
                md_lines.append("")
                for link_id in linked_ids:
                    md_lines.append(f"- [[{link_id}]]")

            exports.append({
                "filename": filename,
                "title": obj.title,
                "id": obj.id,
                "structure_id": obj.structure_id,
                "content": "\n".join(md_lines),
            })

        return exports

    def import_from_json(
        self,
        space_id: str,
        export_data: Dict[str, Any],
        create_new_ids: bool = True,
        skip_existing: bool = True,
    ) -> Dict[str, Any]:
        """Import objects from a JSON export."""
        import uuid as uuid_module
        from datetime import datetime, timezone

        objects_to_import = export_data.get("objects", [])
        if not objects_to_import:
            return {
                "imported_count": 0,
                "skipped_count": 0,
                "failed_count": 0,
                "details": [],
            }

        existing_titles = set()
        if skip_existing:
            existing_objects = self.get_all_objects(space_id)
            existing_titles = {obj.title.lower() for obj in existing_objects}

        imported_count = 0
        skipped_count = 0
        failed_count = 0
        details = []

        id_mapping = {}

        entities_to_create = []
        for obj_data in objects_to_import:
            title = obj_data.get("properties", {}).get("title", {}).get("val", "Untitled")

            if skip_existing and title.lower() in existing_titles:
                skipped_count += 1
                details.append({
                    "title": title,
                    "status": "skipped",
                    "reason": "exists",
                })
                continue

            entity = obj_data.copy()
            old_id = entity.get("id")

            if create_new_ids:
                new_id = str(uuid_module.uuid4())
                id_mapping[old_id] = new_id
                entity["id"] = new_id

            now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            entity["lastUpdated"] = now
            entity["deleteRequested"] = False

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

            entities_to_create.append((title, entity))

        batch_size = 50
        for batch_start in range(0, len(entities_to_create), batch_size):
            batch = entities_to_create[batch_start:batch_start + batch_size]
            entities = [e[1] for e in batch]
            titles = [e[0] for e in batch]

            try:
                results = self._sync_entities(space_id, entities)
                for i, result in enumerate(results):
                    if result.get("status") == "success":
                        imported_count += 1
                        details.append({
                            "title": titles[i] if i < len(titles) else "Unknown",
                            "status": "imported",
                            "id": result.get("id"),
                        })
                    else:
                        failed_count += 1
                        details.append({
                            "title": titles[i] if i < len(titles) else "Unknown",
                            "status": "failed",
                            "reason": str(result),
                        })
            except Exception as e:
                for title in titles:
                    failed_count += 1
                    details.append({
                        "title": title,
                        "status": "failed",
                        "reason": str(e),
                    })

            if batch_start + batch_size < len(entities_to_create):
                time.sleep(0.2)

        return {
            "imported_count": imported_count,
            "skipped_count": skipped_count,
            "failed_count": failed_count,
            "id_mapping": id_mapping if create_new_ids else {},
            "details": details,
        }
