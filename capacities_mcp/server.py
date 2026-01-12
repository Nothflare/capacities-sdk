"""
Capacities MCP Server (FastMCP)

7 action-based tools for AI agents to access Capacities.io (Portal API only).
All responses are JSON for token efficiency.

Environment Variables:
    CAPACITIES_AUTH_TOKEN (required): JWT token from Capacities web app
    CAPACITIES_SPACE_ID (optional): Default space UUID - if set, space_id is optional in all tools
"""

import os
import json
import sys
from typing import Any, Dict, Optional, List

from fastmcp import FastMCP
from fastmcp.dependencies import Depends

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from capacities_sdk import CapacitiesClient, CapacitiesError, TaskStatus, TaskPriority
from capacities_sdk.exceptions import AuthenticationError, NotFoundError, RateLimitError, ValidationError

# =============================================================================
# Configuration
# =============================================================================

AUTH_TOKEN = os.environ.get("CAPACITIES_AUTH_TOKEN")
DEFAULT_SPACE_ID = os.environ.get("CAPACITIES_SPACE_ID")

_BASE_INSTRUCTIONS = """
## What is Capacities?

Capacities is a graph-based Personal Knowledge Management (PKM) app. Core concepts:

- **Object**: The fundamental unit. Everything is an object - notes, pages, people, books, tasks.
- **Structure**: Object type/schema. Built-in types: RootPage, RootTask, RootDailyNote, RootTag. Custom types have UUID IDs.
- **Links**: Objects connect via inline links or embedded blocks. Backlinks show what references an object.
- **Collections**: Groups of objects (like databases/folders).
- **Content**: Markdown auto-parsed into blocks (headings, code, lists, quotes).

## Response Format

All responses are JSON:
- Write ops: `{"ok": true, "id": "..."}` or `{"error": {"code": "...", ...}}`
- Read ops: Arrays or objects directly, no wrapper
- Types shown as names (e.g., "Note") not UUIDs
"""

if DEFAULT_SPACE_ID:
    INSTRUCTIONS = _BASE_INSTRUCTIONS + f"""
## Configuration

Default space: `{DEFAULT_SPACE_ID}` (auto-used, no need to specify space_id)
"""
else:
    INSTRUCTIONS = _BASE_INSTRUCTIONS + """
## Configuration

No default space. First call capacities_space(action="list") to get space_id.
"""

mcp = FastMCP(name="capacities", instructions=INSTRUCTIONS)

# =============================================================================
# State & Dependencies
# =============================================================================

_client: CapacitiesClient = None
_type_map: Dict[str, str] = {}  # UUID -> name
_name_map: Dict[str, str] = {}  # name (lowercase) -> UUID

def get_client() -> CapacitiesClient:
    """Get or create the Capacities client. Caches type maps on first connect."""
    global _client, _type_map, _name_map
    if _client is None:
        if not AUTH_TOKEN:
            raise ValueError("CAPACITIES_AUTH_TOKEN environment variable is required")
        _client = CapacitiesClient(auth_token=AUTH_TOKEN)
        # Cache type maps on first connect
        if DEFAULT_SPACE_ID and not _type_map:
            try:
                structures = _client.get_structures(DEFAULT_SPACE_ID)
                for s in structures:
                    _type_map[s.id] = s.title
                    _name_map[s.title.lower()] = s.id
                # Add built-in types (both directions)
                builtins = {
                    "RootPage": "Page",
                    "RootTask": "Task",
                    "RootDailyNote": "DailyNote",
                    "RootTag": "Tag",
                    "RootDatabase": "Collection",
                    "RootCollection": "Collection",
                    "RootStructure": "Structure",
                    "MediaWebResource": "Weblink",
                    "MediaImage": "Image",
                    "MediaPDF": "PDF",
                }
                _type_map.update(builtins)
                for uuid, name in builtins.items():
                    _name_map[name.lower()] = uuid
            except Exception:
                pass  # Silently fail - will use as-is
    return _client

def get_space_id(space_id: Optional[str] = None) -> str:
    """Get space_id from parameter or default."""
    sid = space_id or DEFAULT_SPACE_ID
    if not sid:
        raise ValueError("space_id is required (no default configured)")
    return sid

def type_name(uuid: str) -> str:
    """Convert structure UUID to readable name."""
    return _type_map.get(uuid, uuid[:8] if len(uuid) > 8 else uuid)

def type_id(name_or_uuid: str) -> str:
    """Convert structure name to UUID. Pass-through if already UUID."""
    if not name_or_uuid:
        return name_or_uuid
    # Check if it's a name (case-insensitive lookup)
    resolved = _name_map.get(name_or_uuid.lower())
    if resolved:
        return resolved
    # Already a UUID or unknown name - pass through
    return name_or_uuid

# =============================================================================
# JSON Response Helpers
# =============================================================================

def ok(id: str = None, ids: List[str] = None, **kw) -> str:
    """Success response for write operations."""
    d = {"ok": True, **kw}
    if id:
        d["id"] = id
    if ids:
        d["ids"] = ids
    return json.dumps(d)

def err(code: str, **kw) -> str:
    """Error response."""
    return json.dumps({"error": {"code": code, **kw}})

def to_object_summary(obj) -> Dict[str, Any]:
    """Object summary for lists."""
    return {"id": obj.id, "title": obj.title, "type": type_name(obj.structure_id)}

def to_object_full(obj) -> Dict[str, Any]:
    """Full object for single get."""
    d = to_object_summary(obj)
    d["content"] = obj.get_content_text()
    # Add custom properties if present
    if hasattr(obj, 'description') and obj.description:
        d.setdefault("props", {})["description"] = obj.description
    return d

def to_task(task) -> Dict[str, Any]:
    """Task for lists."""
    d = {"id": task.id, "title": task.title, "status": task.status.value}
    if task.priority:
        d["priority"] = task.priority.value
    if task.due_date:
        d["due"] = task.due_date.strftime("%Y-%m-%d")
        d["overdue"] = task.is_overdue()
    return d

def handle_error(e: Exception) -> str:
    """Convert exception to error response."""
    if isinstance(e, NotFoundError):
        return err("NOT_FOUND", message=str(e))
    elif isinstance(e, AuthenticationError):
        return err("AUTH_EXPIRED")
    elif isinstance(e, RateLimitError):
        return err("RATE_LIMIT", retry_after=getattr(e, 'retry_after', 60))
    elif isinstance(e, ValidationError):
        return err("VALIDATION", message=str(e))
    elif isinstance(e, ValueError):
        return err("VALIDATION", message=str(e))
    else:
        return err("UNKNOWN", message=str(e))

# =============================================================================
# Tools
# =============================================================================

@mcp.tool
def capacities_objects(
    action: str,
    space_id: Optional[str] = None,
    object_id: Optional[str] = None,
    object_ids: Optional[List[str]] = None,
    structure_id: Optional[str] = None,
    title: Optional[str] = None,
    content: Optional[str] = None,
    old_string: Optional[str] = None,
    new_string: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    query: Optional[str] = None,
    limit: int = 50,
    client: CapacitiesClient = Depends(get_client),
) -> str:
    """
    CRUD operations on objects (notes, pages, etc).

    Actions:
    - list: See all objects. Add structure_id to filter by type (e.g., "RootPage", "RootTask").
    - get: Read full content of one object by object_id.
    - get_many: Read multiple objects by object_ids list.
    - search: Find objects by title matching query.
    - search_content: Full-text search across all content.
    - create: New object. Requires structure_id and title. content is markdown (auto-parsed).
    - update: Modify object_id. For content edits use old_string/new_string (like find-replace). Or pass content to replace all.
    - delete: Move to trash (recoverable).
    - restore: Recover from trash.
    """
    try:
        if action == "get":
            obj = client.get_object(object_id)
            if not obj:
                return err("NOT_FOUND", id=object_id)
            return json.dumps(to_object_full(obj))

        if action == "get_many":
            objects = client.get_objects_by_ids(object_ids or [])
            return json.dumps([to_object_full(o) for o in objects])

        sid = get_space_id(space_id)

        if action == "create":
            sid_resolved = type_id(structure_id)  # Allow "Note" instead of UUID
            obj = client.create_object(sid, sid_resolved, title, content, description, tags)
            return ok(id=obj.id)

        if action == "update":
            final_content = content
            if old_string is not None:
                obj = client.get_object(object_id)
                if not obj:
                    return err("NOT_FOUND", id=object_id)
                current_content = obj.get_content_text() or ""
                if old_string not in current_content:
                    return err("VALIDATION", message="old_string not found in content")
                final_content = current_content.replace(old_string, new_string or "", 1)
            client.update_object(sid, object_id, title, final_content, description, tags)
            return ok(id=object_id)

        if action == "delete":
            client.delete_object(sid, object_id)
            return ok()

        if action == "restore":
            client.restore_object(sid, object_id)
            return ok(id=object_id)

        if action == "list":
            if structure_id:
                sid_resolved = type_id(structure_id)  # Allow "Note" instead of UUID
                objects = client.get_objects_by_structure(sid, sid_resolved)
            else:
                objects = client.get_all_objects(sid)
            objects = objects[:limit]
            return json.dumps([to_object_summary(o) for o in objects])

        if action == "search":
            objects = client.search_by_title(sid, query, limit=limit)
            return json.dumps([to_object_summary(o) for o in objects])

        if action == "search_content":
            objects = client.search_content(sid, query, limit)
            return json.dumps([to_object_summary(o) for o in objects])

        return err("VALIDATION", message=f"Unknown action: {action}")
    except Exception as e:
        return handle_error(e)


@mcp.tool
def capacities_tasks(
    action: str,
    space_id: Optional[str] = None,
    task_id: Optional[str] = None,
    title: Optional[str] = None,
    due_date: Optional[str] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None,
    notes: Optional[str] = None,
    tags: Optional[List[str]] = None,
    client: CapacitiesClient = Depends(get_client),
) -> str:
    """
    Task management with due dates and priorities.

    Actions:
    - list: All tasks. Filter with status (not-started/next-up/done) or priority (high/medium/low).
    - pending: Quick view of incomplete tasks.
    - overdue: Tasks past their due date.
    - create: New task. title required. Optional: due_date (YYYY-MM-DD), priority, notes.
    - complete: Mark task_id as done.
    - uncomplete: Reopen a completed task.
    - update: Change any task field by task_id.
    - delete: Move task to trash.
    """
    try:
        sid = get_space_id(space_id)
        pri = TaskPriority(priority) if priority else None
        sta = TaskStatus(status) if status else None

        if action == "create":
            task = client.create_task(sid, title, due_date, pri, notes, tags)
            return ok(id=task.id)

        if action == "list":
            tasks = client.get_tasks(sid, status=sta, priority=pri)
            return json.dumps([to_task(t) for t in tasks])

        if action == "pending":
            tasks = client.get_pending_tasks(sid)
            return json.dumps([to_task(t) for t in tasks])

        if action == "overdue":
            tasks = client.get_overdue_tasks(sid)
            return json.dumps([to_task(t) for t in tasks])

        if action == "complete":
            client.complete_task(sid, task_id)
            return ok()

        if action == "uncomplete":
            client.uncomplete_task(sid, task_id)
            return ok()

        if action == "update":
            client.update_task(sid, task_id, title, sta, pri, due_date, notes, tags)
            return ok(id=task_id)

        if action == "delete":
            client.delete_task(sid, task_id)
            return ok()

        return err("VALIDATION", message=f"Unknown action: {action}")
    except Exception as e:
        return handle_error(e)


@mcp.tool
def capacities_space(
    action: str,
    space_id: Optional[str] = None,
    object_id: Optional[str] = None,
    depth: int = 2,
    client: CapacitiesClient = Depends(get_client),
) -> str:
    """
    Space info and graph traversal.

    Actions:
    - list: Show all available spaces (useful if no default configured).
    - info: List all structures (object types) in the space with their IDs.
    - graph: Trace connections from object_id up to depth levels (1-3). Shows linked objects.
    """
    try:
        if action == "list":
            spaces = client.get_spaces()
            return json.dumps([{"id": s.id, "title": s.title} for s in spaces])

        if action == "info":
            sid = get_space_id(space_id)
            info = client.get_space_info(sid)
            return json.dumps({
                "structures": [{"id": s["id"], "name": s["title"]} for s in info.get("structures", [])],
                "collections": [{"id": c["id"], "name": c["title"]} for c in info.get("collections", [])]
            })

        if action == "graph":
            summary = client.get_graph_summary(object_id, depth)
            nodes = [
                {"id": nid, "title": info["title"], "depth": info["depth"]}
                for nid, info in summary["nodes"].items()
            ]
            return json.dumps({"root": object_id, "nodes": nodes, "depth": summary["max_depth_reached"]})

        return err("VALIDATION", message=f"Unknown action: {action}")
    except Exception as e:
        return handle_error(e)


@mcp.tool
def capacities_collections(
    action: str,
    space_id: Optional[str] = None,
    object_id: Optional[str] = None,
    collection_id: Optional[str] = None,
    client: CapacitiesClient = Depends(get_client),
) -> str:
    """
    Manage collection (database) membership.

    Actions:
    - list: Show all objects in a collection by collection_id.
    - add: Add object_id to collection_id.
    - remove: Remove object_id from collection_id.
    """
    try:
        sid = get_space_id(space_id)

        if action == "add":
            client.add_to_collection(sid, object_id, collection_id)
            return ok()

        if action == "remove":
            client.remove_from_collection(sid, object_id, collection_id)
            return ok()

        if action == "list":
            objects = client.get_collection_objects(sid, collection_id)
            return json.dumps([to_object_summary(o) for o in objects])

        return err("VALIDATION", message=f"Unknown action: {action}")
    except Exception as e:
        return handle_error(e)


@mcp.tool
def capacities_links(
    action: str,
    space_id: Optional[str] = None,
    object_id: Optional[str] = None,
    source_object_id: Optional[str] = None,
    target_object_id: Optional[str] = None,
    display_text: Optional[str] = None,
    as_block: bool = False,
    client: CapacitiesClient = Depends(get_client),
) -> str:
    """
    Explore and create links between objects.

    Actions:
    - get: See what object_id links TO (outgoing links).
    - get_linked: Get full details of linked objects.
    - backlinks: See what links TO object_id (incoming links). Great for discovering connections.
    - add: Create link from source_object_id to target_object_id. Optional display_text. Set as_block=true for embed.
    """
    try:
        if action == "get":
            links = client.get_links(object_id)
            return json.dumps([
                {"target": l["target_id"], "text": l.get("display_text"), "block": l.get("is_block", False)}
                for l in links
            ])

        if action == "get_linked":
            objects = client.get_linked_objects(object_id)
            return json.dumps([to_object_summary(o) for o in objects])

        sid = get_space_id(space_id)

        if action == "backlinks":
            objects = client.get_backlinks(sid, object_id)
            return json.dumps([to_object_summary(o) for o in objects])

        if action == "add":
            client.add_link(sid, source_object_id, target_object_id, display_text, as_block)
            return ok()

        return err("VALIDATION", message=f"Unknown action: {action}")
    except Exception as e:
        return handle_error(e)


@mcp.tool
def capacities_bulk(
    action: str,
    space_id: Optional[str] = None,
    objects: Optional[List[dict]] = None,
    updates: Optional[List[dict]] = None,
    object_ids: Optional[List[str]] = None,
    title_prefix: str = "Copy of ",
    client: CapacitiesClient = Depends(get_client),
) -> str:
    """
    Batch operations on multiple objects at once.

    Actions:
    - create: Create many objects. objects=[{structure_id, title, content?, description?}, ...]
    - update: Update many. updates=[{object_id, title?, content?, description?}, ...]
    - delete: Delete multiple by object_ids list.
    - clone: Duplicate objects with new IDs. Optional title_prefix (default "Copy of ").
    """
    try:
        sid = get_space_id(space_id)

        if action == "create":
            created = client.bulk_create(sid, objects or [])
            return ok(ids=[o.id for o in created], count=len(created))

        if action == "update":
            updated = client.bulk_update(sid, updates or [])
            return ok(ids=[o.id for o in updated], count=len(updated))

        if action == "delete":
            result = client.bulk_delete(sid, object_ids or [])
            failed_ids = result.get("failed_ids", [])
            return json.dumps({
                "ok": result["failed_count"] == 0,
                "deleted": result["success_count"],
                "failed": failed_ids
            })

        if action == "clone":
            cloned = client.clone_objects(sid, object_ids or [], title_prefix)
            return ok(ids=[o.id for o in cloned], count=len(cloned))

        return err("VALIDATION", message=f"Unknown action: {action}")
    except Exception as e:
        return handle_error(e)


@mcp.tool
def capacities_export(
    action: str,
    space_id: Optional[str] = None,
    include_content: bool = True,
    object_ids: Optional[List[str]] = None,
    export_data: Optional[dict] = None,
    create_new_ids: bool = True,
    skip_existing: bool = True,
    client: CapacitiesClient = Depends(get_client),
) -> str:
    """
    Export and import for backup/migration.

    Actions:
    - space_json: Export entire space to JSON. Set include_content=false for metadata only.
    - markdown: Export objects as markdown files. Optional object_ids to limit scope.
    - import_json: Restore from export_data JSON. create_new_ids=true generates fresh IDs.
    """
    try:
        sid = get_space_id(space_id)

        if action == "space_json":
            data = client.export_space_json(sid, include_content)
            return json.dumps({
                "count": data["object_count"],
                "structures": len(data.get("structures", [])),
                "json": json.dumps(data)
            })

        if action == "markdown":
            exports = client.export_objects_to_markdown(sid, object_ids)
            return json.dumps([
                {"filename": e["filename"], "content": e["content"]}
                for e in exports
            ])

        if action == "import_json":
            result = client.import_from_json(sid, export_data or {}, create_new_ids, skip_existing)
            return json.dumps({
                "ok": result["failed_count"] == 0,
                "imported": result["imported_count"],
                "skipped": result["skipped_count"],
                "failed": result.get("failed_ids", [])
            })

        return err("VALIDATION", message=f"Unknown action: {action}")
    except Exception as e:
        return handle_error(e)


if __name__ == "__main__":
    mcp.run()
