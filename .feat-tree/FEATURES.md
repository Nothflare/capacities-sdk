# Features

> Auto-generated. Do not edit. Use Claude Code to modify.

## MCP
**MCP Server**
Model Context Protocol server exposing Capacities functionality to AI agents

- **Status:** active
- **Files:** capacities_mcp/__init__.py, capacities_mcp/server.py

### MCP.tools_bulk
**Bulk Operation Tools**
MCP bulk operations via capacities_bulk tool - create, update, delete, clone multiple objects

- **Status:** active
- **Files:** capacities_mcp/server.py

### MCP.tools_export
**Export/Import Tools**
MCP export/import via capacities_export tool - space_json, markdown, import_json actions

- **Status:** active
- **Files:** capacities_mcp/server.py

### MCP.tools_read
**Read Tools**
MCP tools for reading spaces, objects, and content via capacities_objects and capacities_space tools

- **Status:** active
- **Files:** capacities_mcp/server.py

### MCP.tools_write
**Write Tools**
MCP tools for creating, updating, deleting objects via capacities_objects and capacities_daily tools

- **Status:** active
- **Files:** capacities_mcp/server.py

## REFACTOR
**QoL Refactor**
Quality of life refactor - split client.py into mixins, consolidate MCP tools with action flags.

- **Status:** active

### REFACTOR.mcp_consolidate
**Consolidated MCP Tools**
Reduce 35 MCP tools to 8 action-based tools to save context window for AI agents.

- **Status:** active
- **Symbols:** capacities_objects, capacities_tasks, capacities_space, capacities_daily, capacities_collections, capacities_links, capacities_bulk, capacities_export
- **Files:** capacities_mcp/server.py
- **Commits:** 635cb48

### REFACTOR.mixins
**Mixin Class Structure**
Split client.py (2000+ LoC) into domain-focused mixin classes for better organization and maintainability.

- **Status:** active
- **Symbols:** ObjectsMixin, TasksMixin, LinksMixin, CollectionsMixin, BulkMixin, ExportMixin, GraphMixin, OfficialAPIMixin
- **Files:** capacities_sdk/client.py, capacities_sdk/mixins/__init__.py, capacities_sdk/mixins/objects.py, capacities_sdk/mixins/tasks.py, capacities_sdk/mixins/links.py, capacities_sdk/mixins/collections.py, capacities_sdk/mixins/bulk.py, capacities_sdk/mixins/export.py, capacities_sdk/mixins/graph.py, capacities_sdk/mixins/official.py
- **Commits:** 1f74b28, fe6028f

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
- **Files:** capacities_sdk/blocks.py, capacities_sdk/models.py

### SDK.bulk
**Bulk Operations**
Bulk operations for creating, updating, deleting and restoring multiple objects in single API calls. Much more efficient than individual operations.

- **Status:** active
- **Symbols:** _sync_entities, bulk_create, bulk_update, bulk_delete, bulk_restore, clone_objects
- **Files:** capacities_sdk/mixins/bulk.py, capacities_mcp/server.py

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
- **Files:** capacities_sdk/mixins/collections.py, capacities_mcp/server.py

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
- **Files:** capacities_sdk/mixins/export.py, capacities_mcp/server.py

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
- **Files:** capacities_sdk/mixins/graph.py

### SDK.links
**Link Creation**
Create bidirectional links between objects programmatically

- **Status:** active
- **Symbols:** LinkNode.from_link_token, Object.get_links, create_link_token, create_entity_block, get_links, get_backlinks, add_link, get_linked_objects
- **Files:** capacities_sdk/mixins/links.py, capacities_sdk/blocks.py, capacities_mcp/server.py

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
- **Files:** capacities_sdk/mixins/official.py

### SDK.read
**Read Operations**
Fetch objects by ID, list all objects in space, filter by type

- **Status:** active
- **Symbols:** get_object, get_objects_by_ids, list_space_objects, get_all_objects, get_objects_by_structure
- **Files:** capacities_sdk/mixins/objects.py

### SDK.search
**Search**
Search objects by title using lookup API

- **Status:** active
- **Symbols:** search_by_title, lookup
- **Files:** capacities_sdk/mixins/objects.py, capacities_sdk/mixins/official.py

### SDK.tasks
**Task Management**
Complete task management - create, list, complete, filter tasks with due dates and priorities

- **Status:** active
- **Symbols:** Task, TaskStatus, TaskPriority, get_tasks, get_pending_tasks, get_overdue_tasks, get_tasks_due_today, get_task, create_task, complete_task, uncomplete_task, set_task_priority, set_task_due_date, update_task, delete_task, format_task
- **Files:** capacities_sdk/mixins/tasks.py, capacities_sdk/models.py, capacities_mcp/server.py

### SDK.write
**Write Operations**
Create, update, delete, and restore objects via sync API

- **Status:** active
- **Symbols:** create_object, update_object, delete_object, restore_object, _sync_entity
- **Files:** capacities_sdk/mixins/objects.py, capacities_sdk/client.py
