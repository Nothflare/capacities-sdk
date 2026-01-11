"""
Capacities MCP Server (FastMCP)

8 action-based tools for AI agents to access Capacities.io.

Environment Variables:
    CAPACITIES_AUTH_TOKEN (required): API token from Capacities settings
    CAPACITIES_SPACE_ID (optional): Default space UUID - if set, space_id is optional in all tools
"""

import os
import json
import sys
from typing import Any, Optional, List

from fastmcp import FastMCP
from fastmcp.dependencies import Depends

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from capacities_sdk import CapacitiesClient, CapacitiesError, TaskStatus, TaskPriority

# =============================================================================
# Configuration
# =============================================================================

AUTH_TOKEN = os.environ.get("CAPACITIES_AUTH_TOKEN")
DEFAULT_SPACE_ID = os.environ.get("CAPACITIES_SPACE_ID")

# Build server instructions based on configuration
_BASE_INSTRUCTIONS = """
## What is Capacities?

Capacities is a graph-based Personal Knowledge Management (PKM) app. Core concepts:

- **Object**: The fundamental unit. Everything is an object - notes, pages, people, books, tasks.
- **Structure**: Object type/schema. Built-in types: RootPage, RootTask, RootDailyNote, RootTag. Custom types have UUID IDs.
- **Links**: Objects connect via inline links or embedded blocks. Backlinks show what references an object.
- **Collections**: Groups of objects (like databases/folders).
- **Content**: Markdown auto-parsed into blocks (headings, code, lists, quotes).
"""

if DEFAULT_SPACE_ID:
    INSTRUCTIONS = _BASE_INSTRUCTIONS + f"""
## Configuration

Default space: `{DEFAULT_SPACE_ID}` (auto-used, no need to specify space_id)

Start exploring with capacities_space or capacities_objects.
"""
else:
    INSTRUCTIONS = _BASE_INSTRUCTIONS + """
## Configuration

No default space. First call capacities_space(action="list") to get space_id.
"""

mcp = FastMCP(name="capacities", instructions=INSTRUCTIONS)

# =============================================================================
# Dependencies
# =============================================================================

_client: CapacitiesClient = None

def get_client() -> CapacitiesClient:
    """Get or create the Capacities client."""
    global _client
    if _client is None:
        if not AUTH_TOKEN:
            raise ValueError("CAPACITIES_AUTH_TOKEN environment variable is required")
        _client = CapacitiesClient(auth_token=AUTH_TOKEN)
    return _client

def get_space_id(space_id: Optional[str] = None) -> str:
    """Get space_id from parameter or default."""
    sid = space_id or DEFAULT_SPACE_ID
    if not sid:
        raise ValueError("space_id is required (no default configured)")
    return sid

# =============================================================================
# Formatters
# =============================================================================

def format_task(task) -> str:
    icons = {TaskStatus.NOT_STARTED: "[ ]", TaskStatus.NEXT_UP: "[>]", TaskStatus.DONE: "[x]"}
    lines = [f"{icons.get(task.status, '[ ]')} **{task.title}**", f"- ID: `{task.id}`", f"- Status: {task.status.value}"]
    if task.priority:
        lines.append(f"- Priority: {task.priority.value}")
    if task.due_date:
        lines.append(f"- Due: {task.due_date.strftime('%Y-%m-%d')}{' (OVERDUE)' if task.is_overdue() else ''}")
    if task.notes:
        lines.append(f"- Notes: {task.notes[:100]}...")
    return "\n".join(lines)

def format_object(obj) -> str:
    lines = [f"## {obj.title}", f"- ID: `{obj.id}`", f"- Type: {obj.structure_id}"]
    if obj.description:
        lines.append(f"- Description: {obj.description}")
    content = obj.get_content_text()
    if content:
        lines.append(f"\n### Content:\n{content[:500]}{'...' if len(content) > 500 else ''}")
    return "\n".join(lines)

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
            return format_object(obj) if obj else f"Not found: {object_id}"

        if action == "get_many":
            objects = client.get_objects_by_ids(object_ids or [])
            return "\n\n---\n\n".join(format_object(o) for o in objects)

        sid = get_space_id(space_id)

        if action == "create":
            obj = client.create_object(sid, structure_id, title, content, description, tags)
            return f"Created!\n\n{format_object(obj)}"

        if action == "update":
            # If old_string/new_string provided, do find-replace on content
            final_content = content
            if old_string is not None:
                obj = client.get_object(object_id)
                if not obj:
                    return f"Not found: {object_id}"
                current_content = obj.get_content_text() or ""
                if old_string not in current_content:
                    return f"Error: old_string not found in content. Use get first to see current content."
                final_content = current_content.replace(old_string, new_string or "", 1)
            obj = client.update_object(sid, object_id, title, final_content, description, tags)
            return f"Updated!\n\n{format_object(obj)}"

        if action == "delete":
            ok = client.delete_object(sid, object_id)
            return "Deleted (moved to trash)" if ok else "Delete failed"

        if action == "restore":
            obj = client.restore_object(sid, object_id)
            return f"Restored!\n\n{format_object(obj)}"

        if action == "list":
            if structure_id:
                objects = client.get_objects_by_structure(sid, structure_id)
            else:
                objects = client.get_all_objects(sid)
            objects = objects[:limit]
            return f"# Objects ({len(objects)})\n\n" + "\n".join(f"- **{o.title}** (`{o.id}`) - {o.structure_id}" for o in objects)

        if action == "search":
            objects = client.search_by_title(sid, query)
            return f"# Search: '{query}' ({len(objects)})\n\n" + "\n".join(f"- **{o.title}** (`{o.id}`)" for o in objects)

        if action == "search_content":
            objects = client.search_content(sid, query, limit)
            return f"# Content Search: '{query}' ({len(objects)})\n\n" + "\n".join(f"- **{o.title}** (`{o.id}`)" for o in objects)

        return f"Unknown action: {action}"
    except Exception as e:
        return f"Error: {e}"


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
            return f"Created!\n\n{format_task(task)}"

        if action == "list":
            tasks = client.get_tasks(sid, status=sta, priority=pri)
            return f"# Tasks ({len(tasks)})\n\n" + "\n\n".join(format_task(t) for t in tasks)

        if action == "pending":
            tasks = client.get_pending_tasks(sid)
            return f"# Pending ({len(tasks)})\n\n" + "\n\n".join(format_task(t) for t in tasks)

        if action == "overdue":
            tasks = client.get_overdue_tasks(sid)
            return f"# Overdue ({len(tasks)})\n\n" + ("\n\n".join(format_task(t) for t in tasks) or "None!")

        if action == "complete":
            task = client.complete_task(sid, task_id)
            return f"Completed!\n\n{format_task(task)}"

        if action == "uncomplete":
            task = client.uncomplete_task(sid, task_id)
            return f"Uncompleted!\n\n{format_task(task)}"

        if action == "update":
            task = client.update_task(sid, task_id, title, sta, pri, due_date, notes, tags)
            return f"Updated!\n\n{format_task(task)}"

        if action == "delete":
            ok = client.delete_task(sid, task_id)
            return "Deleted" if ok else "Delete failed"

        return f"Unknown action: {action}"
    except Exception as e:
        return f"Error: {e}"


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
            return "# Spaces\n\n" + "\n".join(f"- **{s.title}** (`{s.id}`)" for s in spaces)

        if action == "info":
            sid = get_space_id(space_id)
            structs = client.get_structures(sid)
            lines = ["# Structures\n"]
            for s in structs:
                lines.append(f"## {s.title}\n- ID: `{s.id}`\n- Plural: {s.plural_name}\n")
            return "\n".join(lines)

        if action == "graph":
            summary = client.get_graph_summary(object_id, depth)
            result = f"# Graph\n- Nodes: {summary['total_nodes']}\n- Max depth: {summary['max_depth_reached']}\n\n## Nodes\n"
            for nid, info in summary["nodes"].items():
                result += f"{'  ' * info['depth']}- **{info['title']}** (`{nid[:8]}...`)\n"
            return result

        return f"Unknown action: {action}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool
def capacities_daily(
    action: str,
    space_id: Optional[str] = None,
    text: Optional[str] = None,
    no_timestamp: bool = False,
    url: Optional[str] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    notes: Optional[str] = None,
    client: CapacitiesClient = Depends(get_client),
) -> str:
    """
    Quick capture to daily notes and weblinks.

    Actions:
    - note: Append text (markdown) to today's daily note. Set no_timestamp=true to skip timestamp.
    - weblink: Save a URL. Optional: title, description, tags, notes.
    """
    try:
        sid = get_space_id(space_id)

        if action == "note":
            client.save_to_daily_note(sid, text, no_timestamp)
            return "Added to daily note!"

        if action == "weblink":
            result = client.save_weblink(sid, url, title, description, tags, notes)
            return f"Saved weblink: {result.get('title', url)}"

        return f"Unknown action: {action}"
    except Exception as e:
        return f"Error: {e}"


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
            obj = client.add_to_collection(sid, object_id, collection_id)
            return f"Added!\n\n{format_object(obj)}"

        if action == "remove":
            obj = client.remove_from_collection(sid, object_id, collection_id)
            return f"Removed!\n\n{format_object(obj)}"

        if action == "list":
            objects = client.get_collection_objects(sid, collection_id)
            return f"# Collection ({len(objects)})\n\n" + "\n".join(f"- **{o.title}** (`{o.id}`)" for o in objects)

        return f"Unknown action: {action}"
    except Exception as e:
        return f"Error: {e}"


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
            return f"# Links ({len(links)})\n\n" + "\n".join(f"- {l['display_text'] or '(embed)'} → `{l['target_id']}`" for l in links)

        if action == "get_linked":
            objects = client.get_linked_objects(object_id)
            return f"# Linked ({len(objects)})\n\n" + "\n".join(f"- **{o.title}** (`{o.id}`)" for o in objects)

        sid = get_space_id(space_id)

        if action == "backlinks":
            objects = client.get_backlinks(sid, object_id)
            return f"# Backlinks ({len(objects)})\n\n" + "\n".join(f"- **{o.title}** (`{o.id}`)" for o in objects)

        if action == "add":
            obj = client.add_link(sid, source_object_id, target_object_id, display_text, as_block)
            return f"Added {'block' if as_block else 'inline'} link!\n\n{format_object(obj)}"

        return f"Unknown action: {action}"
    except Exception as e:
        return f"Error: {e}"


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
            return f"# Created {len(created)}\n\n" + "\n".join(f"- **{o.title}** (`{o.id}`)" for o in created)

        if action == "update":
            updated = client.bulk_update(sid, updates or [])
            return f"# Updated {len(updated)}\n\n" + "\n".join(f"- **{o.title}** (`{o.id}`)" for o in updated)

        if action == "delete":
            result = client.bulk_delete(sid, object_ids or [])
            return f"Deleted: {result['success_count']}, Failed: {result['failed_count']}"

        if action == "clone":
            cloned = client.clone_objects(sid, object_ids or [], title_prefix)
            return f"# Cloned {len(cloned)}\n\n" + "\n".join(f"- **{o.title}** (`{o.id}`)" for o in cloned)

        return f"Unknown action: {action}"
    except Exception as e:
        return f"Error: {e}"


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
            result = f"# Export\n- Objects: {data['object_count']}\n\n```json\n"
            result += json.dumps(data, indent=2)[:10000]
            return result + "\n```"

        if action == "markdown":
            exports = client.export_objects_to_markdown(sid, object_ids)
            result = f"# Markdown ({len(exports)} files)\n\n"
            for e in exports[:20]:
                result += f"## {e['filename']}\n```markdown\n{e['content'][:500]}\n```\n\n"
            return result

        if action == "import_json":
            result = client.import_from_json(sid, export_data or {}, create_new_ids, skip_existing)
            return f"Imported: {result['imported_count']}, Skipped: {result['skipped_count']}, Failed: {result['failed_count']}"

        return f"Unknown action: {action}"
    except Exception as e:
        return f"Error: {e}"


if __name__ == "__main__":
    mcp.run()
