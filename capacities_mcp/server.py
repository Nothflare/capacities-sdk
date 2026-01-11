"""
Capacities MCP Server

Provides full access to Capacities.io for AI agents via MCP protocol.

Features:
- List and read all objects in a space
- Search by title
- Trace object graphs (1-3 levels deep)
- Save weblinks and daily notes
- View object relationships

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

    # Add content preview
    content = obj.get_content_text()
    if content:
        preview = content[:500] + "..." if len(content) > 500 else content
        lines.append(f"\n### Content:\n{preview}")

    # Add links
    linked_ids = obj.get_linked_object_ids()
    if linked_ids:
        lines.append(f"\n### Links to: {len(linked_ids)} objects")

    return "\n".join(lines)


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="capacities_list_spaces",
            description="List all Capacities spaces you have access to",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="capacities_get_space_info",
            description="Get detailed information about a space including object types (structures) and collections",
            inputSchema={
                "type": "object",
                "properties": {
                    "space_id": {
                        "type": "string",
                        "description": "Space UUID",
                    },
                },
                "required": ["space_id"],
            },
        ),
        Tool(
            name="capacities_list_objects",
            description="List all objects in a space. Returns object IDs and titles. Use capacities_get_object to get full content.",
            inputSchema={
                "type": "object",
                "properties": {
                    "space_id": {
                        "type": "string",
                        "description": "Space UUID",
                    },
                    "structure_id": {
                        "type": "string",
                        "description": "Optional: Filter by object type (e.g., 'RootPage', 'RootDailyNote', 'MediaWebResource')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of objects to return (default: 50)",
                        "default": 50,
                    },
                },
                "required": ["space_id"],
            },
        ),
        Tool(
            name="capacities_get_object",
            description="Get a single object with full content including all text blocks, code blocks, and links",
            inputSchema={
                "type": "object",
                "properties": {
                    "object_id": {
                        "type": "string",
                        "description": "Object UUID",
                    },
                },
                "required": ["object_id"],
            },
        ),
        Tool(
            name="capacities_get_objects",
            description="Get multiple objects by their IDs with full content",
            inputSchema={
                "type": "object",
                "properties": {
                    "object_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of object UUIDs",
                    },
                },
                "required": ["object_ids"],
            },
        ),
        Tool(
            name="capacities_search",
            description="Search for objects by title",
            inputSchema={
                "type": "object",
                "properties": {
                    "space_id": {
                        "type": "string",
                        "description": "Space UUID",
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query (matches against titles)",
                    },
                },
                "required": ["space_id", "query"],
            },
        ),
        Tool(
            name="capacities_trace_graph",
            description="Trace the object graph starting from a given object. Follows links between objects up to a specified depth. Useful for understanding relationships and context.",
            inputSchema={
                "type": "object",
                "properties": {
                    "object_id": {
                        "type": "string",
                        "description": "Starting object UUID",
                    },
                    "depth": {
                        "type": "integer",
                        "description": "How many levels deep to trace (1-3, default: 2)",
                        "default": 2,
                        "minimum": 1,
                        "maximum": 3,
                    },
                },
                "required": ["object_id"],
            },
        ),
        Tool(
            name="capacities_save_weblink",
            description="Save a URL to Capacities with optional title, description, and tags",
            inputSchema={
                "type": "object",
                "properties": {
                    "space_id": {
                        "type": "string",
                        "description": "Space UUID",
                    },
                    "url": {
                        "type": "string",
                        "description": "URL to save",
                    },
                    "title": {
                        "type": "string",
                        "description": "Optional custom title",
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional description",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional tags (must match existing tags or will be created)",
                    },
                    "notes": {
                        "type": "string",
                        "description": "Optional markdown notes to add",
                    },
                },
                "required": ["space_id", "url"],
            },
        ),
        Tool(
            name="capacities_add_to_daily_note",
            description="Add text to today's daily note in a space",
            inputSchema={
                "type": "object",
                "properties": {
                    "space_id": {
                        "type": "string",
                        "description": "Space UUID",
                    },
                    "text": {
                        "type": "string",
                        "description": "Markdown text to add to daily note",
                    },
                    "no_timestamp": {
                        "type": "boolean",
                        "description": "If true, don't add timestamp (default: false)",
                        "default": False,
                    },
                },
                "required": ["space_id", "text"],
            },
        ),
        Tool(
            name="capacities_create_object",
            description="Create a new object (note, page, etc.) in a space. Content is AUTO-PARSED from markdown: # headings, ```code blocks```, - bullet lists, 1. numbered lists, **bold**, *italic*, > quotes, --- dividers. Use capacities_get_space_info first to get available structure_ids.",
            inputSchema={
                "type": "object",
                "properties": {
                    "space_id": {
                        "type": "string",
                        "description": "Space UUID",
                    },
                    "structure_id": {
                        "type": "string",
                        "description": "Structure ID (object type) - get from capacities_get_space_info",
                    },
                    "title": {
                        "type": "string",
                        "description": "Object title",
                    },
                    "content": {
                        "type": "string",
                        "description": "Markdown content (auto-parsed into blocks: headings, code, lists, bold/italic, quotes)",
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional description",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of tag IDs",
                    },
                },
                "required": ["space_id", "structure_id", "title"],
            },
        ),
        Tool(
            name="capacities_update_object",
            description="Update an existing object's title, content, description, or tags. Content is AUTO-PARSED from markdown: # headings, ```code blocks```, - bullet lists, 1. numbered lists, **bold**, *italic*, > quotes, --- dividers.",
            inputSchema={
                "type": "object",
                "properties": {
                    "space_id": {
                        "type": "string",
                        "description": "Space UUID",
                    },
                    "object_id": {
                        "type": "string",
                        "description": "Object UUID to update",
                    },
                    "title": {
                        "type": "string",
                        "description": "New title (optional)",
                    },
                    "content": {
                        "type": "string",
                        "description": "Markdown content (auto-parsed, replaces existing)",
                    },
                    "description": {
                        "type": "string",
                        "description": "New description (optional)",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "New tags list (optional)",
                    },
                },
                "required": ["space_id", "object_id"],
            },
        ),
        Tool(
            name="capacities_delete_object",
            description="Delete an object (moves to trash). Can be restored later.",
            inputSchema={
                "type": "object",
                "properties": {
                    "space_id": {
                        "type": "string",
                        "description": "Space UUID",
                    },
                    "object_id": {
                        "type": "string",
                        "description": "Object UUID to delete",
                    },
                },
                "required": ["space_id", "object_id"],
            },
        ),
        Tool(
            name="capacities_restore_object",
            description="Restore a deleted object from trash",
            inputSchema={
                "type": "object",
                "properties": {
                    "space_id": {
                        "type": "string",
                        "description": "Space UUID",
                    },
                    "object_id": {
                        "type": "string",
                        "description": "Object UUID to restore",
                    },
                },
                "required": ["space_id", "object_id"],
            },
        ),
        # Task Tools
        Tool(
            name="capacities_create_task",
            description="Create a new task in a space with optional due date, priority, and notes",
            inputSchema={
                "type": "object",
                "properties": {
                    "space_id": {
                        "type": "string",
                        "description": "Space UUID",
                    },
                    "title": {
                        "type": "string",
                        "description": "Task title",
                    },
                    "due_date": {
                        "type": "string",
                        "description": "Optional due date (ISO format, e.g., '2025-01-15')",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                        "description": "Optional priority level",
                    },
                    "notes": {
                        "type": "string",
                        "description": "Optional notes content",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of tag IDs",
                    },
                },
                "required": ["space_id", "title"],
            },
        ),
        Tool(
            name="capacities_list_tasks",
            description="List all tasks in a space, optionally filtered by status or priority",
            inputSchema={
                "type": "object",
                "properties": {
                    "space_id": {
                        "type": "string",
                        "description": "Space UUID",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["not-started", "next-up", "done"],
                        "description": "Optional status filter",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                        "description": "Optional priority filter",
                    },
                },
                "required": ["space_id"],
            },
        ),
        Tool(
            name="capacities_get_pending_tasks",
            description="Get all non-completed tasks in a space",
            inputSchema={
                "type": "object",
                "properties": {
                    "space_id": {
                        "type": "string",
                        "description": "Space UUID",
                    },
                },
                "required": ["space_id"],
            },
        ),
        Tool(
            name="capacities_get_overdue_tasks",
            description="Get all overdue tasks (past due date and not completed)",
            inputSchema={
                "type": "object",
                "properties": {
                    "space_id": {
                        "type": "string",
                        "description": "Space UUID",
                    },
                },
                "required": ["space_id"],
            },
        ),
        Tool(
            name="capacities_complete_task",
            description="Mark a task as completed",
            inputSchema={
                "type": "object",
                "properties": {
                    "space_id": {
                        "type": "string",
                        "description": "Space UUID",
                    },
                    "task_id": {
                        "type": "string",
                        "description": "Task UUID to complete",
                    },
                },
                "required": ["space_id", "task_id"],
            },
        ),
        Tool(
            name="capacities_uncomplete_task",
            description="Mark a completed task as not completed",
            inputSchema={
                "type": "object",
                "properties": {
                    "space_id": {
                        "type": "string",
                        "description": "Space UUID",
                    },
                    "task_id": {
                        "type": "string",
                        "description": "Task UUID to uncomplete",
                    },
                },
                "required": ["space_id", "task_id"],
            },
        ),
        Tool(
            name="capacities_update_task",
            description="Update a task's title, status, priority, due date, notes, or tags",
            inputSchema={
                "type": "object",
                "properties": {
                    "space_id": {
                        "type": "string",
                        "description": "Space UUID",
                    },
                    "task_id": {
                        "type": "string",
                        "description": "Task UUID to update",
                    },
                    "title": {
                        "type": "string",
                        "description": "New title (optional)",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["not-started", "next-up", "done"],
                        "description": "New status (optional)",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                        "description": "New priority (optional)",
                    },
                    "due_date": {
                        "type": "string",
                        "description": "New due date as ISO string (optional)",
                    },
                    "notes": {
                        "type": "string",
                        "description": "New notes content (optional)",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "New tags list (optional)",
                    },
                },
                "required": ["space_id", "task_id"],
            },
        ),
        # Collection Tools
        Tool(
            name="capacities_add_to_collection",
            description="Add an object to a collection (database)",
            inputSchema={
                "type": "object",
                "properties": {
                    "space_id": {
                        "type": "string",
                        "description": "Space UUID",
                    },
                    "object_id": {
                        "type": "string",
                        "description": "Object UUID to add",
                    },
                    "collection_id": {
                        "type": "string",
                        "description": "Collection UUID to add to",
                    },
                },
                "required": ["space_id", "object_id", "collection_id"],
            },
        ),
        Tool(
            name="capacities_remove_from_collection",
            description="Remove an object from a collection (database)",
            inputSchema={
                "type": "object",
                "properties": {
                    "space_id": {
                        "type": "string",
                        "description": "Space UUID",
                    },
                    "object_id": {
                        "type": "string",
                        "description": "Object UUID to remove",
                    },
                    "collection_id": {
                        "type": "string",
                        "description": "Collection UUID to remove from",
                    },
                },
                "required": ["space_id", "object_id", "collection_id"],
            },
        ),
        Tool(
            name="capacities_get_collection_objects",
            description="Get all objects in a collection",
            inputSchema={
                "type": "object",
                "properties": {
                    "space_id": {
                        "type": "string",
                        "description": "Space UUID",
                    },
                    "collection_id": {
                        "type": "string",
                        "description": "Collection UUID",
                    },
                },
                "required": ["space_id", "collection_id"],
            },
        ),
        # Full-Text Search Tool
        Tool(
            name="capacities_search_content",
            description="Full-text search across all content in a space (searches inside objects, not just titles)",
            inputSchema={
                "type": "object",
                "properties": {
                    "space_id": {
                        "type": "string",
                        "description": "Space UUID",
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results (default 50)",
                        "default": 50,
                    },
                },
                "required": ["space_id", "query"],
            },
        ),
        # Link Tools
        Tool(
            name="capacities_get_links",
            description="Get all links (references to other objects) from an object's content",
            inputSchema={
                "type": "object",
                "properties": {
                    "object_id": {
                        "type": "string",
                        "description": "Object UUID to get links from",
                    },
                },
                "required": ["object_id"],
            },
        ),
        Tool(
            name="capacities_get_backlinks",
            description="Get all objects that link to a given object (find what references this)",
            inputSchema={
                "type": "object",
                "properties": {
                    "space_id": {
                        "type": "string",
                        "description": "Space UUID",
                    },
                    "object_id": {
                        "type": "string",
                        "description": "Object UUID to find backlinks for",
                    },
                },
                "required": ["space_id", "object_id"],
            },
        ),
        Tool(
            name="capacities_add_link",
            description="Add a link from one object to another (creates inline reference or embedded block)",
            inputSchema={
                "type": "object",
                "properties": {
                    "space_id": {
                        "type": "string",
                        "description": "Space UUID",
                    },
                    "source_object_id": {
                        "type": "string",
                        "description": "Object UUID to add the link to",
                    },
                    "target_object_id": {
                        "type": "string",
                        "description": "Object UUID to link to",
                    },
                    "display_text": {
                        "type": "string",
                        "description": "Text to display for the link (defaults to target title)",
                    },
                    "as_block": {
                        "type": "boolean",
                        "description": "If true, embed as block; if false, add as inline link (default: false)",
                        "default": False,
                    },
                },
                "required": ["space_id", "source_object_id", "target_object_id"],
            },
        ),
        Tool(
            name="capacities_get_linked_objects",
            description="Get all objects that a given object links to (follow outgoing links)",
            inputSchema={
                "type": "object",
                "properties": {
                    "object_id": {
                        "type": "string",
                        "description": "Object UUID to get linked objects from",
                    },
                },
                "required": ["object_id"],
            },
        ),
        # Bulk Operation Tools
        Tool(
            name="capacities_bulk_create",
            description="Create multiple objects in bulk. More efficient than creating one at a time.",
            inputSchema={
                "type": "object",
                "properties": {
                    "space_id": {
                        "type": "string",
                        "description": "Space UUID",
                    },
                    "objects": {
                        "type": "array",
                        "description": "List of objects to create",
                        "items": {
                            "type": "object",
                            "properties": {
                                "structure_id": {
                                    "type": "string",
                                    "description": "Structure ID (object type)",
                                },
                                "title": {
                                    "type": "string",
                                    "description": "Object title",
                                },
                                "content": {
                                    "type": "string",
                                    "description": "Markdown content",
                                },
                                "description": {
                                    "type": "string",
                                    "description": "Object description",
                                },
                                "tags": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Tag IDs",
                                },
                            },
                            "required": ["structure_id", "title"],
                        },
                    },
                },
                "required": ["space_id", "objects"],
            },
        ),
        Tool(
            name="capacities_bulk_update",
            description="Update multiple objects in bulk",
            inputSchema={
                "type": "object",
                "properties": {
                    "space_id": {
                        "type": "string",
                        "description": "Space UUID",
                    },
                    "updates": {
                        "type": "array",
                        "description": "List of updates to apply",
                        "items": {
                            "type": "object",
                            "properties": {
                                "object_id": {
                                    "type": "string",
                                    "description": "Object UUID to update",
                                },
                                "title": {
                                    "type": "string",
                                    "description": "New title",
                                },
                                "content": {
                                    "type": "string",
                                    "description": "New markdown content",
                                },
                                "description": {
                                    "type": "string",
                                    "description": "New description",
                                },
                                "tags": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "New tags",
                                },
                            },
                            "required": ["object_id"],
                        },
                    },
                },
                "required": ["space_id", "updates"],
            },
        ),
        Tool(
            name="capacities_bulk_delete",
            description="Delete multiple objects in bulk (moves to trash)",
            inputSchema={
                "type": "object",
                "properties": {
                    "space_id": {
                        "type": "string",
                        "description": "Space UUID",
                    },
                    "object_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of object UUIDs to delete",
                    },
                },
                "required": ["space_id", "object_ids"],
            },
        ),
        Tool(
            name="capacities_clone_objects",
            description="Clone existing objects with new IDs",
            inputSchema={
                "type": "object",
                "properties": {
                    "space_id": {
                        "type": "string",
                        "description": "Space UUID",
                    },
                    "object_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of object UUIDs to clone",
                    },
                    "title_prefix": {
                        "type": "string",
                        "description": "Prefix for cloned titles (default: 'Copy of ')",
                        "default": "Copy of ",
                    },
                },
                "required": ["space_id", "object_ids"],
            },
        ),
        # Export/Import Tools
        Tool(
            name="capacities_export_space",
            description="Export all objects in a space to JSON format for backup",
            inputSchema={
                "type": "object",
                "properties": {
                    "space_id": {
                        "type": "string",
                        "description": "Space UUID",
                    },
                    "include_content": {
                        "type": "boolean",
                        "description": "Include full content (default: true)",
                        "default": True,
                    },
                },
                "required": ["space_id"],
            },
        ),
        Tool(
            name="capacities_export_markdown",
            description="Export objects as markdown content",
            inputSchema={
                "type": "object",
                "properties": {
                    "space_id": {
                        "type": "string",
                        "description": "Space UUID",
                    },
                    "object_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific object IDs (default: all objects)",
                    },
                },
                "required": ["space_id"],
            },
        ),
        Tool(
            name="capacities_import_json",
            description="Import objects from a JSON export backup",
            inputSchema={
                "type": "object",
                "properties": {
                    "space_id": {
                        "type": "string",
                        "description": "Space UUID to import into",
                    },
                    "export_data": {
                        "type": "object",
                        "description": "JSON export data from capacities_export_space",
                    },
                    "create_new_ids": {
                        "type": "boolean",
                        "description": "Generate new IDs for imported objects (default: true)",
                        "default": True,
                    },
                    "skip_existing": {
                        "type": "boolean",
                        "description": "Skip objects that already exist by title (default: true)",
                        "default": True,
                    },
                },
                "required": ["space_id", "export_data"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
    """Handle tool calls."""
    try:
        client = get_client()

        if name == "capacities_list_spaces":
            spaces = client.get_spaces()
            result = "# Your Capacities Spaces\n\n"
            for space in spaces:
                result += f"- **{space.title}** (`{space.id}`)\n"
            return CallToolResult(content=[TextContent(type="text", text=result)])

        elif name == "capacities_get_space_info":
            space_id = arguments["space_id"]
            structures = client.get_structures(space_id)
            result = f"# Space Structures\n\n"
            for struct in structures:
                result += f"## {struct.title}\n"
                result += f"- ID: `{struct.id}`\n"
                result += f"- Plural: {struct.plural_name}\n"
                if struct.collections:
                    result += f"- Collections: {len(struct.collections)}\n"
                result += "\n"
            return CallToolResult(content=[TextContent(type="text", text=result)])

        elif name == "capacities_list_objects":
            space_id = arguments["space_id"]
            structure_id = arguments.get("structure_id")
            limit = arguments.get("limit", 50)

            if structure_id:
                objects = client.get_objects_by_structure(space_id, structure_id)
            else:
                objects = client.get_all_objects(space_id)

            objects = objects[:limit]

            result = f"# Objects ({len(objects)} shown)\n\n"
            for obj in objects:
                result += f"- **{obj.title}** (`{obj.id}`) - {obj.structure_id}\n"

            return CallToolResult(content=[TextContent(type="text", text=result)])

        elif name == "capacities_get_object":
            object_id = arguments["object_id"]
            obj = client.get_object(object_id)
            if not obj:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Object not found: {object_id}")]
                )
            result = format_object(obj)
            return CallToolResult(content=[TextContent(type="text", text=result)])

        elif name == "capacities_get_objects":
            object_ids = arguments["object_ids"]
            objects = client.get_objects_by_ids(object_ids)
            result = f"# Objects ({len(objects)})\n\n"
            for obj in objects:
                result += format_object(obj) + "\n\n---\n\n"
            return CallToolResult(content=[TextContent(type="text", text=result)])

        elif name == "capacities_search":
            space_id = arguments["space_id"]
            query = arguments["query"]
            objects = client.search_by_title(space_id, query)
            result = f"# Search Results for '{query}' ({len(objects)})\n\n"
            for obj in objects:
                result += f"- **{obj.title}** (`{obj.id}`) - {obj.structure_id}\n"
            return CallToolResult(content=[TextContent(type="text", text=result)])

        elif name == "capacities_trace_graph":
            object_id = arguments["object_id"]
            depth = arguments.get("depth", 2)
            summary = client.get_graph_summary(object_id, depth)

            result = f"# Object Graph\n\n"
            result += f"- **Total nodes**: {summary['total_nodes']}\n"
            result += f"- **Max depth reached**: {summary['max_depth_reached']}\n\n"

            result += "## Node Types\n"
            for type_id, count in summary["type_counts"].items():
                result += f"- {type_id}: {count}\n"

            result += "\n## Nodes\n"
            for node_id, info in summary["nodes"].items():
                indent = "  " * info["depth"]
                result += f"{indent}- **{info['title']}** (`{node_id[:8]}...`) [{info['type']}]\n"
                if info["links"]:
                    result += f"{indent}  Links to: {len(info['links'])} objects\n"

            return CallToolResult(content=[TextContent(type="text", text=result)])

        elif name == "capacities_save_weblink":
            space_id = arguments["space_id"]
            url = arguments["url"]
            result = client.save_weblink(
                space_id=space_id,
                url=url,
                title=arguments.get("title"),
                description=arguments.get("description"),
                tags=arguments.get("tags"),
                md_text=arguments.get("notes"),
            )
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Saved weblink: {result.get('title', url)} (ID: {result.get('id')})",
                    )
                ]
            )

        elif name == "capacities_add_to_daily_note":
            space_id = arguments["space_id"]
            text = arguments["text"]
            no_timestamp = arguments.get("no_timestamp", False)
            client.save_to_daily_note(space_id, text, no_timestamp)
            return CallToolResult(
                content=[TextContent(type="text", text="Added to daily note successfully")]
            )

        elif name == "capacities_create_object":
            space_id = arguments["space_id"]
            structure_id = arguments["structure_id"]
            title = arguments["title"]
            obj = client.create_object(
                space_id=space_id,
                structure_id=structure_id,
                title=title,
                content_text=arguments.get("content"),
                description=arguments.get("description"),
                tags=arguments.get("tags"),
            )
            result = f"Created object successfully!\n\n{format_object(obj)}"
            return CallToolResult(content=[TextContent(type="text", text=result)])

        elif name == "capacities_update_object":
            space_id = arguments["space_id"]
            object_id = arguments["object_id"]
            obj = client.update_object(
                space_id=space_id,
                object_id=object_id,
                title=arguments.get("title"),
                content_text=arguments.get("content"),
                description=arguments.get("description"),
                tags=arguments.get("tags"),
            )
            result = f"Updated object successfully!\n\n{format_object(obj)}"
            return CallToolResult(content=[TextContent(type="text", text=result)])

        elif name == "capacities_delete_object":
            space_id = arguments["space_id"]
            object_id = arguments["object_id"]
            success = client.delete_object(space_id, object_id)
            if success:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Deleted object {object_id} successfully (moved to trash)")]
                )
            else:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Failed to delete object {object_id}")]
                )

        elif name == "capacities_restore_object":
            space_id = arguments["space_id"]
            object_id = arguments["object_id"]
            obj = client.restore_object(space_id, object_id)
            result = f"Restored object successfully!\n\n{format_object(obj)}"
            return CallToolResult(content=[TextContent(type="text", text=result)])

        # Task Tool Handlers
        elif name == "capacities_create_task":
            space_id = arguments["space_id"]
            title = arguments["title"]
            priority = None
            if arguments.get("priority"):
                priority = TaskPriority(arguments["priority"])
            task = client.create_task(
                space_id=space_id,
                title=title,
                due_date=arguments.get("due_date"),
                priority=priority,
                notes=arguments.get("notes"),
                tags=arguments.get("tags"),
            )
            result = f"Created task successfully!\n\n{format_task(task)}"
            return CallToolResult(content=[TextContent(type="text", text=result)])

        elif name == "capacities_list_tasks":
            space_id = arguments["space_id"]
            status = None
            priority = None
            if arguments.get("status"):
                status = TaskStatus(arguments["status"])
            if arguments.get("priority"):
                priority = TaskPriority(arguments["priority"])
            tasks = client.get_tasks(space_id, status=status, priority=priority)
            result = f"# Tasks ({len(tasks)})\n\n"
            for task in tasks:
                result += format_task(task) + "\n\n"
            return CallToolResult(content=[TextContent(type="text", text=result)])

        elif name == "capacities_get_pending_tasks":
            space_id = arguments["space_id"]
            tasks = client.get_pending_tasks(space_id)
            result = f"# Pending Tasks ({len(tasks)})\n\n"
            for task in tasks:
                result += format_task(task) + "\n\n"
            return CallToolResult(content=[TextContent(type="text", text=result)])

        elif name == "capacities_get_overdue_tasks":
            space_id = arguments["space_id"]
            tasks = client.get_overdue_tasks(space_id)
            result = f"# Overdue Tasks ({len(tasks)})\n\n"
            if not tasks:
                result += "No overdue tasks!"
            for task in tasks:
                result += format_task(task) + "\n\n"
            return CallToolResult(content=[TextContent(type="text", text=result)])

        elif name == "capacities_complete_task":
            space_id = arguments["space_id"]
            task_id = arguments["task_id"]
            task = client.complete_task(space_id, task_id)
            result = f"Task completed!\n\n{format_task(task)}"
            return CallToolResult(content=[TextContent(type="text", text=result)])

        elif name == "capacities_uncomplete_task":
            space_id = arguments["space_id"]
            task_id = arguments["task_id"]
            task = client.uncomplete_task(space_id, task_id)
            result = f"Task marked as not completed!\n\n{format_task(task)}"
            return CallToolResult(content=[TextContent(type="text", text=result)])

        elif name == "capacities_update_task":
            space_id = arguments["space_id"]
            task_id = arguments["task_id"]
            status = None
            priority = None
            if arguments.get("status"):
                status = TaskStatus(arguments["status"])
            if arguments.get("priority"):
                priority = TaskPriority(arguments["priority"])
            task = client.update_task(
                space_id=space_id,
                task_id=task_id,
                title=arguments.get("title"),
                status=status,
                priority=priority,
                due_date=arguments.get("due_date"),
                notes=arguments.get("notes"),
                tags=arguments.get("tags"),
            )
            result = f"Task updated!\n\n{format_task(task)}"
            return CallToolResult(content=[TextContent(type="text", text=result)])

        # Collection Tool Handlers
        elif name == "capacities_add_to_collection":
            space_id = arguments["space_id"]
            object_id = arguments["object_id"]
            collection_id = arguments["collection_id"]
            obj = client.add_to_collection(space_id, object_id, collection_id)
            result = f"Added to collection!\n\n{format_object(obj)}"
            return CallToolResult(content=[TextContent(type="text", text=result)])

        elif name == "capacities_remove_from_collection":
            space_id = arguments["space_id"]
            object_id = arguments["object_id"]
            collection_id = arguments["collection_id"]
            obj = client.remove_from_collection(space_id, object_id, collection_id)
            result = f"Removed from collection!\n\n{format_object(obj)}"
            return CallToolResult(content=[TextContent(type="text", text=result)])

        elif name == "capacities_get_collection_objects":
            space_id = arguments["space_id"]
            collection_id = arguments["collection_id"]
            objects = client.get_collection_objects(space_id, collection_id)
            result = f"# Collection Objects ({len(objects)})\n\n"
            for obj in objects:
                result += f"- **{obj.title}** (`{obj.id}`) - {obj.structure_id}\n"
            return CallToolResult(content=[TextContent(type="text", text=result)])

        # Full-Text Search Handler
        elif name == "capacities_search_content":
            space_id = arguments["space_id"]
            query = arguments["query"]
            limit = arguments.get("limit", 50)
            objects = client.search_content(space_id, query, limit)
            result = f"# Content Search: '{query}' ({len(objects)} results)\n\n"
            for obj in objects:
                result += f"- **{obj.title}** (`{obj.id}`) - {obj.structure_id}\n"
                # Show preview of matching content
                content = obj.get_content_text()
                if content and query.lower() in content.lower():
                    # Find the match context
                    idx = content.lower().find(query.lower())
                    start = max(0, idx - 30)
                    end = min(len(content), idx + len(query) + 30)
                    preview = content[start:end]
                    if start > 0:
                        preview = "..." + preview
                    if end < len(content):
                        preview = preview + "..."
                    result += f"  > {preview}\n"
            return CallToolResult(content=[TextContent(type="text", text=result)])

        # Link Tool Handlers
        elif name == "capacities_get_links":
            object_id = arguments["object_id"]
            links = client.get_links(object_id)
            result = f"# Links from Object ({len(links)})\n\n"
            if not links:
                result += "No links found in this object's content."
            for link in links:
                result += f"- **{link['display_text'] or '(embedded)'}** → `{link['target_id']}`\n"
                result += f"  - Type: {link['type']}\n"
                if link['target_structure_id']:
                    result += f"  - Structure: {link['target_structure_id']}\n"
            return CallToolResult(content=[TextContent(type="text", text=result)])

        elif name == "capacities_get_backlinks":
            space_id = arguments["space_id"]
            object_id = arguments["object_id"]
            backlinks = client.get_backlinks(space_id, object_id)
            result = f"# Backlinks ({len(backlinks)} objects link to this)\n\n"
            if not backlinks:
                result += "No objects link to this one."
            for obj in backlinks:
                result += f"- **{obj.title}** (`{obj.id}`) - {obj.structure_id}\n"
            return CallToolResult(content=[TextContent(type="text", text=result)])

        elif name == "capacities_add_link":
            space_id = arguments["space_id"]
            source_id = arguments["source_object_id"]
            target_id = arguments["target_object_id"]
            display_text = arguments.get("display_text")
            as_block = arguments.get("as_block", False)
            obj = client.add_link(
                space_id=space_id,
                source_object_id=source_id,
                target_object_id=target_id,
                display_text=display_text,
                as_block=as_block,
            )
            link_type = "embedded block" if as_block else "inline link"
            result = f"Added {link_type} successfully!\n\n{format_object(obj)}"
            return CallToolResult(content=[TextContent(type="text", text=result)])

        elif name == "capacities_get_linked_objects":
            object_id = arguments["object_id"]
            linked = client.get_linked_objects(object_id)
            result = f"# Linked Objects ({len(linked)})\n\n"
            if not linked:
                result += "This object doesn't link to any other objects."
            for obj in linked:
                result += f"- **{obj.title}** (`{obj.id}`) - {obj.structure_id}\n"
            return CallToolResult(content=[TextContent(type="text", text=result)])

        # Bulk Operation Handlers
        elif name == "capacities_bulk_create":
            space_id = arguments["space_id"]
            objects = arguments["objects"]
            created = client.bulk_create(space_id, objects)
            result = f"# Bulk Create Results\n\n"
            result += f"**Created {len(created)} objects**\n\n"
            for obj in created:
                result += f"- **{obj.title}** (`{obj.id}`)\n"
            return CallToolResult(content=[TextContent(type="text", text=result)])

        elif name == "capacities_bulk_update":
            space_id = arguments["space_id"]
            updates = arguments["updates"]
            updated = client.bulk_update(space_id, updates)
            result = f"# Bulk Update Results\n\n"
            result += f"**Updated {len(updated)} objects**\n\n"
            for obj in updated:
                result += f"- **{obj.title}** (`{obj.id}`)\n"
            return CallToolResult(content=[TextContent(type="text", text=result)])

        elif name == "capacities_bulk_delete":
            space_id = arguments["space_id"]
            object_ids = arguments["object_ids"]
            result_data = client.bulk_delete(space_id, object_ids)
            result = f"# Bulk Delete Results\n\n"
            result += f"- **Deleted**: {result_data['success_count']}\n"
            result += f"- **Failed**: {result_data['failed_count']}\n"
            if result_data['failed_ids']:
                result += f"\n**Failed IDs**: {', '.join(result_data['failed_ids'])}\n"
            return CallToolResult(content=[TextContent(type="text", text=result)])

        elif name == "capacities_clone_objects":
            space_id = arguments["space_id"]
            object_ids = arguments["object_ids"]
            title_prefix = arguments.get("title_prefix", "Copy of ")
            cloned = client.clone_objects(space_id, object_ids, title_prefix)
            result = f"# Clone Results\n\n"
            result += f"**Cloned {len(cloned)} objects**\n\n"
            for obj in cloned:
                result += f"- **{obj.title}** (`{obj.id}`)\n"
            return CallToolResult(content=[TextContent(type="text", text=result)])

        # Export/Import Handlers
        elif name == "capacities_export_space":
            space_id = arguments["space_id"]
            include_content = arguments.get("include_content", True)
            export_data = client.export_space_json(space_id, include_content)
            result = f"# Space Export\n\n"
            result += f"- **Space ID**: {export_data['space_id']}\n"
            result += f"- **Exported At**: {export_data['exported_at']}\n"
            result += f"- **Object Count**: {export_data['object_count']}\n"
            result += f"- **Structures**: {len(export_data['structures'])}\n\n"
            result += "## Export Data\n\n"
            result += "```json\n"
            result += json.dumps(export_data, indent=2)[:10000]  # Truncate for display
            if len(json.dumps(export_data)) > 10000:
                result += "\n... (truncated)"
            result += "\n```"
            return CallToolResult(content=[TextContent(type="text", text=result)])

        elif name == "capacities_export_markdown":
            space_id = arguments["space_id"]
            object_ids = arguments.get("object_ids")
            exports = client.export_objects_to_markdown(space_id, object_ids)
            result = f"# Markdown Export ({len(exports)} files)\n\n"
            for exp in exports[:20]:  # Show first 20
                result += f"## {exp['filename']}\n\n"
                result += f"```markdown\n{exp['content'][:500]}"
                if len(exp['content']) > 500:
                    result += "\n... (truncated)"
                result += "\n```\n\n"
            if len(exports) > 20:
                result += f"\n... and {len(exports) - 20} more files"
            return CallToolResult(content=[TextContent(type="text", text=result)])

        elif name == "capacities_import_json":
            space_id = arguments["space_id"]
            export_data = arguments["export_data"]
            create_new_ids = arguments.get("create_new_ids", True)
            skip_existing = arguments.get("skip_existing", True)
            import_result = client.import_from_json(
                space_id, export_data, create_new_ids, skip_existing
            )
            result = f"# Import Results\n\n"
            result += f"- **Imported**: {import_result['imported_count']}\n"
            result += f"- **Skipped**: {import_result['skipped_count']}\n"
            result += f"- **Failed**: {import_result['failed_count']}\n"
            if import_result['details']:
                result += "\n## Details\n\n"
                for detail in import_result['details'][:50]:
                    status_icon = {"imported": "+", "skipped": "~", "failed": "-"}.get(
                        detail['status'], "?"
                    )
                    result += f"[{status_icon}] {detail['title']}"
                    if detail.get('reason'):
                        result += f" ({detail['reason']})"
                    result += "\n"
            return CallToolResult(content=[TextContent(type="text", text=result)])

        else:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Unknown tool: {name}")]
            )

    except CapacitiesError as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {e.message}")]
        )
    except Exception as e:
        logger.exception("Unexpected error")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Unexpected error: {str(e)}")]
        )


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
