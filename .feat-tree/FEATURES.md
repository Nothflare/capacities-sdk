# Features

> Auto-generated. Do not edit. Use Claude Code to modify.

## MCP
**MCP Server**
Model Context Protocol server exposing Capacities functionality to AI agents

- **Status:** active
- **Files:** capacities_mcp/__init__.py, capacities_mcp/server.py

### MCP.tools_bulk
**Bulk Operation Tools**
MCP tools for bulk operations - create, update, delete multiple objects efficiently in single operations.

- **Status:** active
- **Files:** capacities_mcp/server.py

### MCP.tools_export
**Export/Import Tools**
MCP tools for exporting and importing space data - backup to JSON, export as markdown, restore from backup.

- **Status:** active
- **Files:** capacities_mcp/server.py

### MCP.tools_read
**Read Tools**
MCP tools for listing spaces, objects, and fetching content

- **Status:** active
- **Files:** capacities_mcp/server.py

### MCP.tools_write
**Write Tools**
MCP tools for creating, updating, deleting objects and saving weblinks

- **Status:** active
- **Files:** capacities_mcp/server.py

## REFACTOR
**QoL Refactor**
Quality of life refactor - split client.py into mixins, consolidate MCP tools with action flags.

- **Status:** planned

### REFACTOR.mcp_consolidate
**Consolidated MCP Tools**
Reduce 35 MCP tools to 8 action-based tools to save context window for AI agents.

- **Status:** planned
- **Files:** capacities_mcp/server.py

### REFACTOR.mixins
**Mixin Class Structure**
Split client.py (2000+ LoC) into domain-focused mixin classes for better organization and maintainability.

- **Status:** planned
- **Files:** capacities_sdk/client.py, capacities_sdk/mixins/__init__.py

## SDK
**Capacities SDK**
Unofficial Python SDK providing full CRUD access to Capacities.io via reverse-engineered internal APIs

- **Status:** active
- **Files:** capacities_sdk/__init__.py, capacities_sdk/client.py, capacities_sdk/models.py, capacities_sdk/exceptions.py

### SDK.blocks
**Rich Block Types**
Support for CodeBlock, HeadingBlock, ListBlock, TableBlock, etc.

- **Status:** active
- **Symbols:** markdown_to_blocks, blocks_to_markdown, create_text_block, create_heading_block, create_code_block, create_horizontal_line_block, create_quote_block, parse_inline_formatting, HeadingBlock
- **Files:** capacities_sdk/blocks.py, capacities_sdk/models.py, capacities_sdk/client.py, capacities_mcp/server.py

### SDK.bulk
**Bulk Operations**
Bulk operations for creating, updating, deleting and restoring multiple objects in single API calls. Much more efficient than individual operations.

- **Status:** active
- **Symbols:** _sync_entities, bulk_create, bulk_update, bulk_delete, bulk_restore, clone_objects
- **Files:** capacities_sdk/client.py, capacities_mcp/server.py, capacities_sdk/test_bulk_export.py

### SDK.client
**API Client**
Core HTTP client handling authentication and requests to both internal and official APIs

- **Status:** active
- **Symbols:** CapacitiesClient, _request, _setup_session
- **Files:** capacities_sdk/client.py

### SDK.collections
**Collection Management**
Add/remove objects from collections (databases)

- **Status:** active
- **Symbols:** add_to_collection, remove_from_collection, get_object_collections, get_collection_objects
- **Files:** capacities_sdk/client.py, capacities_mcp/server.py

### SDK.exceptions
**Exception Handling**
Custom exceptions for API errors, auth failures, rate limits, and sync issues

- **Status:** active
- **Files:** capacities_sdk/exceptions.py

### SDK.export
**Export/Import**
Export all objects in a space to JSON or Markdown format for backup. Import from JSON to restore or migrate data between spaces.

- **Status:** active
- **Symbols:** export_space_json, export_objects_to_markdown, import_from_json
- **Files:** capacities_sdk/client.py, capacities_mcp/server.py, capacities_sdk/test_bulk_export.py

### SDK.fulltext
**Full-text Search**
Search content, not just titles

- **Status:** active
- **Symbols:** search_content, _search_content_fallback
- **Files:** capacities_sdk/client.py, capacities_mcp/server.py

### SDK.graph
**Graph Traversal**
Trace object connections and relationships up to 3 levels deep

- **Status:** active
- **Symbols:** trace_graph, get_graph_summary
- **Files:** capacities_sdk/client.py

### SDK.links
**Link Creation**
Create bidirectional links between objects programmatically

- **Status:** active
- **Symbols:** LinkNode.from_link_token, Object.get_links, create_link_token, create_entity_block, get_links, get_backlinks, add_link, get_linked_objects
- **Files:** capacities_sdk/models.py, capacities_sdk/blocks.py, capacities_sdk/client.py, capacities_mcp/server.py

### SDK.models
**Data Models**
Python dataclasses representing Capacities objects, blocks, properties, and graph nodes

- **Status:** active
- **Symbols:** Object, Block, GraphNode
- **Files:** capacities_sdk/models.py

### SDK.official
**Official API Integration**
Integration with official Capacities API for spaces, weblinks, and daily notes

- **Status:** active
- **Symbols:** get_spaces, get_space_info, save_weblink, save_to_daily_note
- **Files:** capacities_sdk/client.py

### SDK.read
**Read Operations**
Fetch objects by ID, list all objects in space, filter by type

- **Status:** active
- **Symbols:** get_object, get_objects_by_ids, list_space_objects, get_all_objects, get_objects_by_structure
- **Files:** capacities_sdk/client.py

### SDK.search
**Search**
Search objects by title using lookup API

- **Status:** active
- **Symbols:** search_by_title, lookup
- **Files:** capacities_sdk/client.py

### SDK.tasks
**Task Management**
Complete task management - create, list, complete, filter tasks with due dates and priorities

- **Status:** active
- **Symbols:** Task, TaskStatus, TaskPriority, get_tasks, get_pending_tasks, get_overdue_tasks, get_tasks_due_today, get_task, create_task, complete_task, uncomplete_task, set_task_priority, set_task_due_date, update_task, delete_task, format_task
- **Files:** capacities_sdk/models.py, capacities_sdk/client.py, capacities_mcp/server.py

### SDK.write
**Write Operations**
Create, update, delete, and restore objects via sync API

- **Status:** active
- **Symbols:** create_object, update_object, delete_object, restore_object, _sync_entity
- **Files:** capacities_sdk/client.py
