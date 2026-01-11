"""
Capacities MCP Server

Provides full access to Capacities.io for AI agents via MCP protocol.

8 consolidated tools:
- capacities_objects: CRUD operations on objects
- capacities_tasks: Task management
- capacities_space: Space info and graph traversal
- capacities_daily: Daily notes and weblinks
- capacities_collections: Collection membership
- capacities_links: Link operations
- capacities_bulk: Bulk operations
- capacities_export: Export/import

Usage:
    Set CAPACITIES_AUTH_TOKEN environment variable, then run:
    $ python -m capacities_mcp.server
"""

import os
import json
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    CallToolResult,
)

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from capacities_sdk import CapacitiesClient, CapacitiesError, TaskStatus, TaskPriority

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("capacities-mcp")

# Initialize server
server = Server("capacities-mcp")

# Global client instance
_client: CapacitiesClient = None


def get_client() -> CapacitiesClient:
    """Get or create the Capacities client."""
    global _client
    if _client is None:
        auth_token = os.environ.get("CAPACITIES_AUTH_TOKEN")
        if not auth_token:
            raise ValueError(
                "CAPACITIES_AUTH_TOKEN environment variable is required. "
                "Get your token from Capacities Desktop App > Settings > Capacities API"
            )
        _client = CapacitiesClient(auth_token=auth_token)
    return _client


def format_task(task) -> str:
    """Format a task for display."""
    status_icons = {
        TaskStatus.NOT_STARTED: "[ ]",
        TaskStatus.NEXT_UP: "[>]",
        TaskStatus.DONE: "[x]",
    }
    priority_labels = {
        TaskPriority.HIGH: "HIGH",
        TaskPriority.MEDIUM: "MED",
        TaskPriority.LOW: "LOW",
    }

    icon = status_icons.get(task.status, "[ ]")
    lines = [f"{icon} **{task.title}**"]
    lines.append(f"- **ID**: `{task.id}`")
    lines.append(f"- **Status**: {task.status.value}")

    if task.priority:
        lines.append(f"- **Priority**: {priority_labels.get(task.priority, task.priority.value)}")
    if task.due_date:
        due_str = task.due_date.strftime("%Y-%m-%d")
        overdue = " (OVERDUE)" if task.is_overdue() else ""
        lines.append(f"- **Due**: {due_str}{overdue}")
    if task.completed_at:
        lines.append(f"- **Completed**: {task.completed_at.strftime('%Y-%m-%d %H:%M')}")
    if task.notes:
        lines.append(f"- **Notes**: {task.notes[:100]}{'...' if len(task.notes) > 100 else ''}")
    if task.tags:
        lines.append(f"- **Tags**: {', '.join(task.tags)}")

    return "\n".join(lines)


def format_object(obj) -> str:
    """Format an object for display."""
    lines = [
        f"## {obj.title}",
        f"- **ID**: `{obj.id}`",
        f"- **Type**: {obj.structure_id}",
    ]
    if obj.description:
        lines.append(f"- **Description**: {obj.description}")
    if obj.created_at:
        lines.append(f"- **Created**: {obj.created_at.isoformat()}")
    if obj.last_updated:
        lines.append(f"- **Updated**: {obj.last_updated.isoformat()}")
    if obj.tags:
        lines.append(f"- **Tags**: {', '.join(obj.tags)}")

    content = obj.get_content_text()
    if content:
        preview = content[:500] + "..." if len(content) > 500 else content
        lines.append(f"\n### Content:\n{preview}")

    linked_ids = obj.get_linked_object_ids()
    if linked_ids:
        lines.append(f"\n### Links to: {len(linked_ids)} objects")

    return "\n".join(lines)


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        # =================================================================
        # OBJECTS TOOL
        # =================================================================
        Tool(
            name="capacities_objects",
            description="Object CRUD operations. Actions: create, get, get_many, update, delete, restore, list, search, search_content",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["create", "get", "get_many", "update", "delete", "restore", "list", "search", "search_content"],
                        "description": "Action to perform",
                    },
                    "space_id": {
                        "type": "string",
                        "description": "Space UUID (required for create, update, delete, restore, list, search, search_content)",
                    },
                    "object_id": {
                        "type": "string",
                        "description": "Object UUID (for get, update, delete, restore)",
                    },
                    "object_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Object UUIDs (for get_many)",
                    },
                    "structure_id": {
                        "type": "string",
                        "description": "Object type ID (for create, or filter for list)",
                    },
                    "title": {
                        "type": "string",
                        "description": "Object title (for create, update)",
                    },
                    "content": {
                        "type": "string",
                        "description": "Markdown content - auto-parsed into blocks (for create, update)",
                    },
                    "description": {
                        "type": "string",
                        "description": "Object description (for create, update)",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tag IDs (for create, update)",
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query (for search, search_content)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results (for list, search_content)",
                        "default": 50,
                    },
                },
                "required": ["action"],
            },
        ),
        # =================================================================
        # TASKS TOOL
        # =================================================================
        Tool(
            name="capacities_tasks",
            description="Task management. Actions: create, list, pending, overdue, complete, uncomplete, update, delete",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["create", "list", "pending", "overdue", "complete", "uncomplete", "update", "delete"],
                        "description": "Action to perform",
                    },
                    "space_id": {
                        "type": "string",
                        "description": "Space UUID (required for all actions)",
                    },
                    "task_id": {
                        "type": "string",
                        "description": "Task UUID (for complete, uncomplete, update, delete)",
                    },
                    "title": {
                        "type": "string",
                        "description": "Task title (for create, update)",
                    },
                    "due_date": {
                        "type": "string",
                        "description": "Due date ISO format e.g. '2025-01-15' (for create, update)",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                        "description": "Priority level (for create, update, list filter)",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["not-started", "next-up", "done"],
                        "description": "Status (for update, list filter)",
                    },
                    "notes": {
                        "type": "string",
                        "description": "Notes content (for create, update)",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tag IDs (for create, update)",
                    },
                },
                "required": ["action", "space_id"],
            },
        ),
        # =================================================================
        # SPACE TOOL
        # =================================================================
        Tool(
            name="capacities_space",
            description="Space info and navigation. Actions: list, info, graph",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["list", "info", "graph"],
                        "description": "Action: list=all spaces, info=space structures, graph=trace object graph",
                    },
                    "space_id": {
                        "type": "string",
                        "description": "Space UUID (for info)",
                    },
                    "object_id": {
                        "type": "string",
                        "description": "Starting object UUID (for graph)",
                    },
                    "depth": {
                        "type": "integer",
                        "description": "Graph traversal depth 1-3 (for graph)",
                        "default": 2,
                        "minimum": 1,
                        "maximum": 3,
                    },
                },
                "required": ["action"],
            },
        ),
        # =================================================================
        # DAILY TOOL
        # =================================================================
        Tool(
            name="capacities_daily",
            description="Daily notes and weblinks. Actions: note, weblink",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["note", "weblink"],
                        "description": "Action: note=add to daily note, weblink=save URL",
                    },
                    "space_id": {
                        "type": "string",
                        "description": "Space UUID",
                    },
                    "text": {
                        "type": "string",
                        "description": "Markdown text to add (for note)",
                    },
                    "no_timestamp": {
                        "type": "boolean",
                        "description": "Skip timestamp (for note)",
                        "default": False,
                    },
                    "url": {
                        "type": "string",
                        "description": "URL to save (for weblink)",
                    },
                    "title": {
                        "type": "string",
                        "description": "Custom title (for weblink)",
                    },
                    "description": {
                        "type": "string",
                        "description": "Description (for weblink)",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags (for weblink)",
                    },
                    "notes": {
                        "type": "string",
                        "description": "Markdown notes (for weblink)",
                    },
                },
                "required": ["action", "space_id"],
            },
        ),
        # =================================================================
        # COLLECTIONS TOOL
        # =================================================================
        Tool(
            name="capacities_collections",
            description="Collection membership. Actions: add, remove, list",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["add", "remove", "list"],
                        "description": "Action to perform",
                    },
                    "space_id": {
                        "type": "string",
                        "description": "Space UUID",
                    },
                    "object_id": {
                        "type": "string",
                        "description": "Object UUID (for add, remove)",
                    },
                    "collection_id": {
                        "type": "string",
                        "description": "Collection UUID",
                    },
                },
                "required": ["action", "space_id", "collection_id"],
            },
        ),
        # =================================================================
        # LINKS TOOL
        # =================================================================
        Tool(
            name="capacities_links",
            description="Link operations. Actions: get, backlinks, add, get_linked",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["get", "backlinks", "add", "get_linked"],
                        "description": "Action to perform",
                    },
                    "space_id": {
                        "type": "string",
                        "description": "Space UUID (for backlinks, add)",
                    },
                    "object_id": {
                        "type": "string",
                        "description": "Object UUID (for get, backlinks, get_linked)",
                    },
                    "source_object_id": {
                        "type": "string",
                        "description": "Source object UUID (for add)",
                    },
                    "target_object_id": {
                        "type": "string",
                        "description": "Target object UUID (for add)",
                    },
                    "display_text": {
                        "type": "string",
                        "description": "Link display text (for add)",
                    },
                    "as_block": {
                        "type": "boolean",
                        "description": "Embed as block vs inline (for add)",
                        "default": False,
                    },
                },
                "required": ["action"],
            },
        ),
        # =================================================================
        # BULK TOOL
        # =================================================================
        Tool(
            name="capacities_bulk",
            description="Bulk operations. Actions: create, update, delete, clone",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["create", "update", "delete", "clone"],
                        "description": "Action to perform",
                    },
                    "space_id": {
                        "type": "string",
                        "description": "Space UUID",
                    },
                    "objects": {
                        "type": "array",
                        "description": "Objects to create (for create)",
                        "items": {
                            "type": "object",
                            "properties": {
                                "structure_id": {"type": "string"},
                                "title": {"type": "string"},
                                "content": {"type": "string"},
                                "description": {"type": "string"},
                                "tags": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": ["structure_id", "title"],
                        },
                    },
                    "updates": {
                        "type": "array",
                        "description": "Updates to apply (for update)",
                        "items": {
                            "type": "object",
                            "properties": {
                                "object_id": {"type": "string"},
                                "title": {"type": "string"},
                                "content": {"type": "string"},
                                "description": {"type": "string"},
                                "tags": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": ["object_id"],
                        },
                    },
                    "object_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Object IDs (for delete, clone)",
                    },
                    "title_prefix": {
                        "type": "string",
                        "description": "Clone title prefix (for clone)",
                        "default": "Copy of ",
                    },
                },
                "required": ["action", "space_id"],
            },
        ),
        # =================================================================
        # EXPORT TOOL
        # =================================================================
        Tool(
            name="capacities_export",
            description="Export/import. Actions: space_json, markdown, import_json",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["space_json", "markdown", "import_json"],
                        "description": "Action to perform",
                    },
                    "space_id": {
                        "type": "string",
                        "description": "Space UUID",
                    },
                    "include_content": {
                        "type": "boolean",
                        "description": "Include full content (for space_json)",
                        "default": True,
                    },
                    "object_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific object IDs (for markdown)",
                    },
                    "export_data": {
                        "type": "object",
                        "description": "JSON export data (for import_json)",
                    },
                    "create_new_ids": {
                        "type": "boolean",
                        "description": "Generate new IDs (for import_json)",
                        "default": True,
                    },
                    "skip_existing": {
                        "type": "boolean",
                        "description": "Skip existing by title (for import_json)",
                        "default": True,
                    },
                },
                "required": ["action", "space_id"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
    """Handle tool calls."""
    try:
        client = get_client()
        action = arguments.get("action", "")

        # =================================================================
        # OBJECTS TOOL
        # =================================================================
        if name == "capacities_objects":
            if action == "create":
                obj = client.create_object(
                    space_id=arguments["space_id"],
                    structure_id=arguments["structure_id"],
                    title=arguments["title"],
                    content=arguments.get("content"),
                    description=arguments.get("description"),
                    tags=arguments.get("tags"),
                )
                return CallToolResult(content=[TextContent(type="text", text=f"Created object!\n\n{format_object(obj)}")])

            elif action == "get":
                obj = client.get_object(arguments["object_id"])
                if not obj:
                    return CallToolResult(content=[TextContent(type="text", text=f"Object not found: {arguments['object_id']}")])
                return CallToolResult(content=[TextContent(type="text", text=format_object(obj))])

            elif action == "get_many":
                objects = client.get_objects_by_ids(arguments["object_ids"])
                result = f"# Objects ({len(objects)})\n\n"
                for obj in objects:
                    result += format_object(obj) + "\n\n---\n\n"
                return CallToolResult(content=[TextContent(type="text", text=result)])

            elif action == "update":
                obj = client.update_object(
                    space_id=arguments["space_id"],
                    object_id=arguments["object_id"],
                    title=arguments.get("title"),
                    content=arguments.get("content"),
                    description=arguments.get("description"),
                    tags=arguments.get("tags"),
                )
                return CallToolResult(content=[TextContent(type="text", text=f"Updated object!\n\n{format_object(obj)}")])

            elif action == "delete":
                success = client.delete_object(arguments["space_id"], arguments["object_id"])
                msg = "Deleted (moved to trash)" if success else "Delete failed"
                return CallToolResult(content=[TextContent(type="text", text=msg)])

            elif action == "restore":
                obj = client.restore_object(arguments["space_id"], arguments["object_id"])
                return CallToolResult(content=[TextContent(type="text", text=f"Restored!\n\n{format_object(obj)}")])

            elif action == "list":
                space_id = arguments["space_id"]
                structure_id = arguments.get("structure_id")
                limit = arguments.get("limit", 50)
                if structure_id:
                    objects = client.get_objects_by_structure(space_id, structure_id)
                else:
                    objects = client.get_all_objects(space_id)
                objects = objects[:limit]
                result = f"# Objects ({len(objects)})\n\n"
                for obj in objects:
                    result += f"- **{obj.title}** (`{obj.id}`) - {obj.structure_id}\n"
                return CallToolResult(content=[TextContent(type="text", text=result)])

            elif action == "search":
                objects = client.search_by_title(arguments["space_id"], arguments["query"])
                result = f"# Search: '{arguments['query']}' ({len(objects)})\n\n"
                for obj in objects:
                    result += f"- **{obj.title}** (`{obj.id}`) - {obj.structure_id}\n"
                return CallToolResult(content=[TextContent(type="text", text=result)])

            elif action == "search_content":
                limit = arguments.get("limit", 50)
                objects = client.search_content(arguments["space_id"], arguments["query"], limit)
                result = f"# Content Search: '{arguments['query']}' ({len(objects)})\n\n"
                for obj in objects:
                    result += f"- **{obj.title}** (`{obj.id}`)\n"
                return CallToolResult(content=[TextContent(type="text", text=result)])

        # =================================================================
        # TASKS TOOL
        # =================================================================
        elif name == "capacities_tasks":
            space_id = arguments["space_id"]

            if action == "create":
                priority = TaskPriority(arguments["priority"]) if arguments.get("priority") else None
                task = client.create_task(
                    space_id=space_id,
                    title=arguments["title"],
                    due_date=arguments.get("due_date"),
                    priority=priority,
                    notes=arguments.get("notes"),
                    tags=arguments.get("tags"),
                )
                return CallToolResult(content=[TextContent(type="text", text=f"Created task!\n\n{format_task(task)}")])

            elif action == "list":
                status = TaskStatus(arguments["status"]) if arguments.get("status") else None
                priority = TaskPriority(arguments["priority"]) if arguments.get("priority") else None
                tasks = client.get_tasks(space_id, status=status, priority=priority)
                result = f"# Tasks ({len(tasks)})\n\n"
                for task in tasks:
                    result += format_task(task) + "\n\n"
                return CallToolResult(content=[TextContent(type="text", text=result)])

            elif action == "pending":
                tasks = client.get_pending_tasks(space_id)
                result = f"# Pending Tasks ({len(tasks)})\n\n"
                for task in tasks:
                    result += format_task(task) + "\n\n"
                return CallToolResult(content=[TextContent(type="text", text=result)])

            elif action == "overdue":
                tasks = client.get_overdue_tasks(space_id)
                result = f"# Overdue Tasks ({len(tasks)})\n\n"
                if not tasks:
                    result += "No overdue tasks!"
                for task in tasks:
                    result += format_task(task) + "\n\n"
                return CallToolResult(content=[TextContent(type="text", text=result)])

            elif action == "complete":
                task = client.complete_task(space_id, arguments["task_id"])
                return CallToolResult(content=[TextContent(type="text", text=f"Completed!\n\n{format_task(task)}")])

            elif action == "uncomplete":
                task = client.uncomplete_task(space_id, arguments["task_id"])
                return CallToolResult(content=[TextContent(type="text", text=f"Uncompleted!\n\n{format_task(task)}")])

            elif action == "update":
                status = TaskStatus(arguments["status"]) if arguments.get("status") else None
                priority = TaskPriority(arguments["priority"]) if arguments.get("priority") else None
                task = client.update_task(
                    space_id=space_id,
                    task_id=arguments["task_id"],
                    title=arguments.get("title"),
                    status=status,
                    priority=priority,
                    due_date=arguments.get("due_date"),
                    notes=arguments.get("notes"),
                    tags=arguments.get("tags"),
                )
                return CallToolResult(content=[TextContent(type="text", text=f"Updated!\n\n{format_task(task)}")])

            elif action == "delete":
                success = client.delete_task(space_id, arguments["task_id"])
                msg = "Deleted (moved to trash)" if success else "Delete failed"
                return CallToolResult(content=[TextContent(type="text", text=msg)])

        # =================================================================
        # SPACE TOOL
        # =================================================================
        elif name == "capacities_space":
            if action == "list":
                spaces = client.get_spaces()
                result = "# Your Spaces\n\n"
                for space in spaces:
                    result += f"- **{space.title}** (`{space.id}`)\n"
                return CallToolResult(content=[TextContent(type="text", text=result)])

            elif action == "info":
                structures = client.get_structures(arguments["space_id"])
                result = "# Space Structures\n\n"
                for struct in structures:
                    result += f"## {struct.title}\n"
                    result += f"- ID: `{struct.id}`\n"
                    result += f"- Plural: {struct.plural_name}\n"
                    if struct.collections:
                        result += f"- Collections: {len(struct.collections)}\n"
                    result += "\n"
                return CallToolResult(content=[TextContent(type="text", text=result)])

            elif action == "graph":
                depth = arguments.get("depth", 2)
                summary = client.get_graph_summary(arguments["object_id"], depth)
                result = f"# Object Graph\n\n"
                result += f"- **Total nodes**: {summary['total_nodes']}\n"
                result += f"- **Max depth**: {summary['max_depth_reached']}\n\n"
                result += "## Node Types\n"
                for type_id, count in summary["type_counts"].items():
                    result += f"- {type_id}: {count}\n"
                result += "\n## Nodes\n"
                for node_id, info in summary["nodes"].items():
                    indent = "  " * info["depth"]
                    result += f"{indent}- **{info['title']}** (`{node_id[:8]}...`)\n"
                return CallToolResult(content=[TextContent(type="text", text=result)])

        # =================================================================
        # DAILY TOOL
        # =================================================================
        elif name == "capacities_daily":
            space_id = arguments["space_id"]

            if action == "note":
                client.save_to_daily_note(space_id, arguments["text"], arguments.get("no_timestamp", False))
                return CallToolResult(content=[TextContent(type="text", text="Added to daily note!")])

            elif action == "weblink":
                result = client.save_weblink(
                    space_id=space_id,
                    url=arguments["url"],
                    title=arguments.get("title"),
                    description=arguments.get("description"),
                    tags=arguments.get("tags"),
                    md_text=arguments.get("notes"),
                )
                return CallToolResult(content=[TextContent(type="text", text=f"Saved weblink: {result.get('title', arguments['url'])}")])

        # =================================================================
        # COLLECTIONS TOOL
        # =================================================================
        elif name == "capacities_collections":
            space_id = arguments["space_id"]
            collection_id = arguments["collection_id"]

            if action == "add":
                obj = client.add_to_collection(space_id, arguments["object_id"], collection_id)
                return CallToolResult(content=[TextContent(type="text", text=f"Added to collection!\n\n{format_object(obj)}")])

            elif action == "remove":
                obj = client.remove_from_collection(space_id, arguments["object_id"], collection_id)
                return CallToolResult(content=[TextContent(type="text", text=f"Removed from collection!\n\n{format_object(obj)}")])

            elif action == "list":
                objects = client.get_collection_objects(space_id, collection_id)
                result = f"# Collection Objects ({len(objects)})\n\n"
                for obj in objects:
                    result += f"- **{obj.title}** (`{obj.id}`)\n"
                return CallToolResult(content=[TextContent(type="text", text=result)])

        # =================================================================
        # LINKS TOOL
        # =================================================================
        elif name == "capacities_links":
            if action == "get":
                links = client.get_links(arguments["object_id"])
                result = f"# Links ({len(links)})\n\n"
                if not links:
                    result += "No links found."
                for link in links:
                    result += f"- **{link['display_text'] or '(embedded)'}** → `{link['target_id']}`\n"
                return CallToolResult(content=[TextContent(type="text", text=result)])

            elif action == "backlinks":
                backlinks = client.get_backlinks(arguments["space_id"], arguments["object_id"])
                result = f"# Backlinks ({len(backlinks)})\n\n"
                if not backlinks:
                    result += "No backlinks found."
                for obj in backlinks:
                    result += f"- **{obj.title}** (`{obj.id}`)\n"
                return CallToolResult(content=[TextContent(type="text", text=result)])

            elif action == "add":
                obj = client.add_link(
                    space_id=arguments["space_id"],
                    source_object_id=arguments["source_object_id"],
                    target_object_id=arguments["target_object_id"],
                    display_text=arguments.get("display_text"),
                    as_block=arguments.get("as_block", False),
                )
                link_type = "block" if arguments.get("as_block") else "inline"
                return CallToolResult(content=[TextContent(type="text", text=f"Added {link_type} link!\n\n{format_object(obj)}")])

            elif action == "get_linked":
                linked = client.get_linked_objects(arguments["object_id"])
                result = f"# Linked Objects ({len(linked)})\n\n"
                if not linked:
                    result += "No linked objects."
                for obj in linked:
                    result += f"- **{obj.title}** (`{obj.id}`)\n"
                return CallToolResult(content=[TextContent(type="text", text=result)])

        # =================================================================
        # BULK TOOL
        # =================================================================
        elif name == "capacities_bulk":
            space_id = arguments["space_id"]

            if action == "create":
                created = client.bulk_create(space_id, arguments["objects"])
                result = f"# Bulk Create: {len(created)} objects\n\n"
                for obj in created:
                    result += f"- **{obj.title}** (`{obj.id}`)\n"
                return CallToolResult(content=[TextContent(type="text", text=result)])

            elif action == "update":
                updated = client.bulk_update(space_id, arguments["updates"])
                result = f"# Bulk Update: {len(updated)} objects\n\n"
                for obj in updated:
                    result += f"- **{obj.title}** (`{obj.id}`)\n"
                return CallToolResult(content=[TextContent(type="text", text=result)])

            elif action == "delete":
                result_data = client.bulk_delete(space_id, arguments["object_ids"])
                result = f"# Bulk Delete\n\n"
                result += f"- Deleted: {result_data['success_count']}\n"
                result += f"- Failed: {result_data['failed_count']}\n"
                return CallToolResult(content=[TextContent(type="text", text=result)])

            elif action == "clone":
                prefix = arguments.get("title_prefix", "Copy of ")
                cloned = client.clone_objects(space_id, arguments["object_ids"], prefix)
                result = f"# Cloned: {len(cloned)} objects\n\n"
                for obj in cloned:
                    result += f"- **{obj.title}** (`{obj.id}`)\n"
                return CallToolResult(content=[TextContent(type="text", text=result)])

        # =================================================================
        # EXPORT TOOL
        # =================================================================
        elif name == "capacities_export":
            space_id = arguments["space_id"]

            if action == "space_json":
                include_content = arguments.get("include_content", True)
                export_data = client.export_space_json(space_id, include_content)
                result = f"# Export\n\n"
                result += f"- Objects: {export_data['object_count']}\n"
                result += f"- Structures: {len(export_data['structures'])}\n\n"
                result += "```json\n"
                result += json.dumps(export_data, indent=2)[:10000]
                if len(json.dumps(export_data)) > 10000:
                    result += "\n... (truncated)"
                result += "\n```"
                return CallToolResult(content=[TextContent(type="text", text=result)])

            elif action == "markdown":
                exports = client.export_objects_to_markdown(space_id, arguments.get("object_ids"))
                result = f"# Markdown Export ({len(exports)} files)\n\n"
                for exp in exports[:20]:
                    result += f"## {exp['filename']}\n\n```markdown\n{exp['content'][:500]}"
                    if len(exp['content']) > 500:
                        result += "\n..."
                    result += "\n```\n\n"
                if len(exports) > 20:
                    result += f"... and {len(exports) - 20} more"
                return CallToolResult(content=[TextContent(type="text", text=result)])

            elif action == "import_json":
                import_result = client.import_from_json(
                    space_id,
                    arguments["export_data"],
                    arguments.get("create_new_ids", True),
                    arguments.get("skip_existing", True),
                )
                result = f"# Import Results\n\n"
                result += f"- Imported: {import_result['imported_count']}\n"
                result += f"- Skipped: {import_result['skipped_count']}\n"
                result += f"- Failed: {import_result['failed_count']}\n"
                return CallToolResult(content=[TextContent(type="text", text=result)])

        return CallToolResult(content=[TextContent(type="text", text=f"Unknown: {name}/{action}")])

    except CapacitiesError as e:
        return CallToolResult(content=[TextContent(type="text", text=f"Error: {e.message}")])
    except Exception as e:
        logger.exception("Unexpected error")
        return CallToolResult(content=[TextContent(type="text", text=f"Error: {str(e)}")])


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
