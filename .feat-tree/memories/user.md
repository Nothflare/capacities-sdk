# User

**Who:** Developer who paid for Capacities Pro and wants programmatic access for AI agents

**Original Problem:** Official API has NO endpoint to read object content. Only weblinks and daily notes for writes, only search by title for reads.

**Solution Delivered (COMPLETE):**
- Full CRUD via reverse-engineered Portal API
- 8 MCP tools (36 actions) for AI agent integration
- 44 SDK methods across 8 mixins
- Task management with priorities and due dates
- Markdown auto-parsing for natural content creation
- Find-replace editing (old_string/new_string like Edit tool)
- Link creation and backlink discovery
- Collection management
- Full-text content search
- Bulk operations (create, update, delete, clone)
- Export/import (JSON backup, markdown export, restore)
- Default space_id via CAPACITIES_SPACE_ID env var

**User Context:**
- ~450 objects in their space
- 58 objects with links
- 26 tasks
- 34 structures (including custom)
- Multiple collections

**Usage Pattern:**
- Primary: AI agents via MCP tools (Claude can explore graph, manage tasks, create notes)
- Secondary: Python SDK for automation scripts
- Backup: Export space to JSON for safekeeping

**Key UX Improvements:**
- CAPACITIES_SPACE_ID: Set once, never specify space_id again
- Server instructions: Claude understands Capacities domain model
- Find-replace: Edit content naturally with old_string/new_string
- FastMCP: Clean, maintainable server code
