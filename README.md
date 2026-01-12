# Capacities SDK & MCP Server

Unofficial Python SDK and MCP server for [Capacities.io](https://capacities.io) with **full CRUD access** - Create, Read, Update, and Delete any object programmatically.

## Features

- **Full CRUD Operations** - Create, read, update, delete any object
- **Find-Replace Editing** - Update content with old_string/new_string (like Edit tool)
- **Task Management** - Create tasks with due dates, priorities, completion tracking
- **Markdown Auto-Parsing** - Content automatically converts to headings, code blocks, lists, quotes
- **Link Management** - Create inline links, entity embeds, find backlinks
- **Collection Management** - Add/remove objects from collections
- **Full-Text Search** - Search across all content, not just titles
- **Bulk Operations** - Create, update, delete, clone multiple objects efficiently
- **Export/Import** - Backup to JSON, export to Markdown, restore from backup
- **Graph Traversal** - Trace object connections (1-3 levels deep)
- **MCP Server** - 7 action-based tools with FastMCP, auto space_id support
- **Portal API Only** - Single JWT token for all operations, no public API dependency

## Installation

Using [uv](https://docs.astral.sh/uv/) (recommended):

```bash
uv sync
```

Or with pip:

```bash
pip install -e .
```

## Authentication

This SDK uses the **Portal API** which requires a JWT session token. Get it from:

1. **Web App** (recommended): Open https://app.capacities.io, then from browser DevTools:
   - Application → Local Storage → `auth-token`, OR
   - Network tab → any request → `auth-token` header

The token looks like: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6...`

Set the environment variable:

```bash
export CAPACITIES_AUTH_TOKEN="eyJhbG..."
```

## SDK Usage

### Basic Usage

```python
from capacities_sdk import CapacitiesClient

# Initialize client
client = CapacitiesClient(auth_token="your-token")

# Get all objects in a space
objects = client.get_all_objects(space_id="your-space-id")
for obj in objects:
    print(f"{obj.title} - {obj.structure_id}")
```

### Create Objects with Markdown

Content is automatically parsed from markdown:

```python
# Create a note with rich content
note = client.create_object(
    space_id="your-space-id",
    structure_id=note_structure_id,
    title="My Note",
    content="""
# Main Heading

This is **bold** and *italic* text.

> A blockquote

- Bullet point 1
- Bullet point 2

1. Numbered item
2. Another item

## Code Example

```python
def hello():
    print("Hello World")
```

---

Supported markdown:
- `# Headings` (levels 1-6)
- `**bold**` and `*italic*`
- ` ```code blocks``` ` with language
- `- Bullet lists` and `1. Numbered lists`
- `---` Horizontal rules
- `> Blockquotes`

### Task Management

```python
from capacities_sdk import TaskPriority, TaskStatus

# Create a task
task = client.create_task(
    space_id="space-uuid",
    title="Review PR",
    due_date="2025-01-20",
    priority=TaskPriority.HIGH,
    notes="Check the authentication changes"
)

# Complete a task
client.complete_task(space_id, task.id)

# Get pending tasks
pending = client.get_pending_tasks(space_id)

# Get overdue tasks
overdue = client.get_overdue_tasks(space_id)

# Get tasks due today
today = client.get_tasks_due_today(space_id)

# Update task
client.update_task(
    space_id, task.id,
    status=TaskStatus.NEXT_UP,
    priority=TaskPriority.MEDIUM
)
```

### Bulk Operations

```python
# Create multiple objects at once
objects = [
    {"structure_id": note_id, "title": "Note 1", "content": "Content 1"},
    {"structure_id": note_id, "title": "Note 2", "content": "Content 2"},
    {"structure_id": note_id, "title": "Note 3", "content": "Content 3"},
]
created = client.bulk_create(space_id, objects)

# Update multiple objects
updates = [
    {"object_id": "uuid1", "title": "New Title 1"},
    {"object_id": "uuid2", "content": "New content"},
]
updated = client.bulk_update(space_id, updates)

# Delete multiple objects
result = client.bulk_delete(space_id, ["uuid1", "uuid2", "uuid3"])
print(f"Deleted: {result['success_count']}")

# Clone objects
cloned = client.clone_objects(space_id, ["uuid1", "uuid2"], "Copy of ")
```

### Export/Import

```python
# Export entire space to JSON
export_data = client.export_space_json(space_id)
print(f"Exported {export_data['object_count']} objects")

# Save to file
import json
with open("backup.json", "w") as f:
    json.dump(export_data, f)

# Export to Markdown
md_exports = client.export_objects_to_markdown(space_id)
for exp in md_exports:
    with open(f"exports/{exp['filename']}", "w") as f:
        f.write(exp['content'])

# Import from JSON backup
with open("backup.json") as f:
    backup = json.load(f)

result = client.import_from_json(
    space_id=target_space_id,
    export_data=backup,
    create_new_ids=True,   # Generate new IDs
    skip_existing=True     # Skip duplicates by title
)
print(f"Imported: {result['imported_count']}")
```

### Link Management

```python
# Add inline link from one object to another
client.add_link(
    space_id="space-uuid",
    source_object_id="source-uuid",
    target_object_id="target-uuid",
    display_text="See related note"
)

# Add as embedded block
client.add_link(
    space_id, source_id, target_id,
    as_block=True  # Creates EntityBlock embed
)

# Get links from an object
links = client.get_links(object_id)
for link in links:
    print(f"{link['display_text']} -> {link['target_id']}")

# Find backlinks (what links TO this object)
backlinks = client.get_backlinks(space_id, object_id)

# Get full objects that are linked
linked_objects = client.get_linked_objects(object_id)
```

### Collection Management

```python
# Add object to collection
client.add_to_collection(space_id, object_id, collection_id)

# Remove from collection
client.remove_from_collection(space_id, object_id, collection_id)

# Get all objects in a collection
items = client.get_collection_objects(space_id, collection_id)

# Get which collections an object belongs to
collections = client.get_object_collections(object_id)
```

### Full-Text Search

```python
# Search content (not just titles)
results = client.search_content(space_id, "machine learning", limit=20)
for obj in results:
    print(f"{obj.title}: {obj.get_content_text()[:100]}...")
```

### Read Objects

```python
# Get a single object with full content
obj = client.get_object("object-uuid")
print(obj.title)
print(obj.get_content_text())

# Get links from content
links = obj.get_links()

# Get multiple objects
objects = client.get_objects_by_ids(["uuid1", "uuid2"])

# Get objects by type
pages = client.get_objects_by_structure(space_id, "RootPage")
tasks = client.get_objects_by_structure(space_id, "RootTask")
```

### Update Objects

```python
updated = client.update_object(
    space_id="your-space-id",
    object_id="object-uuid",
    title="Updated Title",
    content="New **markdown** content",  # Auto-parsed
    description="New description"
)
```

### Delete and Restore

```python
# Delete (moves to trash)
client.delete_object(space_id, object_id)

# Restore from trash
restored = client.restore_object(space_id, object_id)

# Bulk delete and restore
client.bulk_delete(space_id, [id1, id2, id3])
client.bulk_restore(space_id, [id1, id2, id3])
```

### Graph Traversal

```python
# Trace connections from an object
nodes = client.trace_graph(
    start_object_id="uuid",
    max_depth=2,
    direction="both"  # "outgoing", "incoming", or "both"
)

for node in nodes:
    print(f"{'  ' * node.depth}{node.object.title}")

# Get graph summary
summary = client.get_graph_summary("uuid", max_depth=2)
print(f"Total connected: {summary['total_nodes']}")
```

## MCP Server

The MCP server exposes all SDK functionality to AI agents via **8 action-based tools**.

### Setup for Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "capacities": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/capacities-rev", "python", "-m", "capacities_mcp.server"],
      "env": {
        "CAPACITIES_AUTH_TOKEN": "your-token-here",
        "CAPACITIES_SPACE_ID": "your-space-uuid (optional - auto-fills space_id in all tools)"
      }
    }
  }
}
```

Or without uv:

```json
{
  "mcpServers": {
    "capacities": {
      "command": "python",
      "args": ["-m", "capacities_mcp.server"],
      "cwd": "/path/to/capacities-rev",
      "env": {
        "CAPACITIES_AUTH_TOKEN": "your-token-here",
        "CAPACITIES_SPACE_ID": "your-space-uuid (optional)"
      }
    }
  }
}
```

**Tip:** Set `CAPACITIES_SPACE_ID` if you only have one space - then you never need to specify `space_id` in tool calls.

### Available MCP Tools

| Tool | Actions | Description |
|------|---------|-------------|
| `capacities_objects` | create, get, get_many, update, delete, restore, list, search, search_content | Object CRUD operations |
| `capacities_tasks` | create, list, pending, overdue, complete, uncomplete, update, delete | Task management |
| `capacities_space` | list, info, graph | Space info and navigation |
| `capacities_collections` | add, remove, list | Collection membership |
| `capacities_links` | get, backlinks, add, get_linked | Link operations |
| `capacities_bulk` | create, update, delete, clone | Bulk operations |
| `capacities_export` | space_json, markdown, import_json | Export/import |

### Response Format

All responses are **token-efficient JSON**:

```json
// Write operations - minimal confirmation
{"ok": true, "id": "343e24b1-..."}

// Read operations - data directly, no wrapper
[{"id": "...", "title": "My Note", "type": "Note"}]

// Errors - typed codes
{"error": {"code": "NOT_FOUND", "id": "..."}}
```

### Type Name Mapping

Use readable names instead of UUIDs for `structure_id`:

```python
# These are equivalent:
capacities_objects(action="create", structure_id="Note", title="My Note")
capacities_objects(action="create", structure_id="02df2623-...", title="My Note")

# Works for list filtering too:
capacities_objects(action="list", structure_id="Task")
```

### Example Usage

```python
# List all spaces (if CAPACITIES_SPACE_ID not set)
capacities_space(action="list")

# Get space structures (object types)
capacities_space(action="info")

# Create an object (use type name or UUID)
capacities_objects(action="create", structure_id="Note", title="My Note", content="# Hello\n\nWorld")

# Find-replace edit (like Edit tool)
capacities_objects(action="update", object_id="...", old_string="World", new_string="Universe")

# Replace all content
capacities_objects(action="update", object_id="...", content="Completely new content")

# Create a task
capacities_tasks(action="create", title="Review PR", priority="high", due_date="2025-01-20")

# Complete a task
capacities_tasks(action="complete", task_id="...")

# Explore graph connections
capacities_space(action="graph", object_id="...", depth=2)
```

## Object Model

### Structure IDs (Built-in Types)

| Type | Structure ID |
|------|--------------|
| Page | `RootPage` |
| Daily Note | `RootDailyNote` |
| Tag | `RootTag` |
| Task | `RootTask` |
| Weblink | `MediaWebResource` |
| Image | `MediaImage` |
| PDF | `MediaPDF` |
| AI Chat | `RootAIChat` |
| Table | `RootSimpleTable` |
| Collection | `RootDatabase` |

Custom object types have UUID structure IDs - use `get_structures()` to find them.

### Object Properties

```python
obj.id              # UUID
obj.title           # Title
obj.description     # Description
obj.structure_id    # Object type
obj.created_at      # Creation timestamp
obj.last_updated    # Last update timestamp
obj.tags            # List of tag names
obj.properties      # Dict of all properties
obj.blocks          # Dict of content blocks
obj.raw_data        # Original API response

# Methods
obj.get_content_text()      # All text as string
obj.get_links()             # List of LinkNode objects
obj.get_linked_object_ids() # List of linked IDs
```

### Task Properties

```python
task.id             # UUID
task.title          # Title
task.status         # TaskStatus enum (NOT_STARTED, NEXT_UP, DONE)
task.priority       # TaskPriority enum (HIGH, MEDIUM, LOW)
task.due_date       # datetime or None
task.completed_at   # datetime or None
task.notes          # Notes content

# Methods
task.is_completed()  # bool
task.is_overdue()    # bool
task.is_due_today()  # bool
```

## Project Structure

```
capacities-rev/
├── capacities_sdk/          # Python SDK
│   ├── client.py            # Main client (inherits from mixins)
│   ├── mixins/              # Feature-specific mixins
│   │   ├── objects.py       # CRUD operations
│   │   ├── tasks.py         # Task management
│   │   ├── links.py         # Link operations
│   │   ├── collections.py   # Collection membership
│   │   ├── bulk.py          # Bulk operations
│   │   ├── export.py        # Export/import
│   │   ├── graph.py         # Graph traversal
│   │   └── official.py      # Official API endpoints
│   ├── models.py            # Data models
│   └── blocks.py            # Markdown parsing
├── capacities_mcp/          # MCP server
│   └── server.py            # FastMCP server (8 tools)
├── tests/                   # Test files
│   ├── test_tasks.py
│   ├── test_blocks.py
│   ├── test_links.py
│   ├── test_collections_search.py
│   └── test_bulk_export.py
├── pyproject.toml           # Project config
└── uv.lock                  # Dependency lock
```

## Testing

Run tests with pytest:

```bash
uv run pytest
```

Or run individual test files:

```bash
uv run pytest tests/test_tasks.py -v
```

## SDK Summary

| Category | SDK Methods | MCP Tool |
|----------|-------------|----------|
| Objects | 11 | `capacities_objects` (9 actions) |
| Tasks | 12 | `capacities_tasks` (8 actions) |
| Space | 4 | `capacities_space` (3 actions) |
| Collections | 4 | `capacities_collections` (3 actions) |
| Links | 4 | `capacities_links` (4 actions) |
| Bulk | 5 | `capacities_bulk` (4 actions) |
| Export | 3 | `capacities_export` (3 actions) |
| **Total** | **43** | **7 tools, 34 actions** |

## License

MIT License
