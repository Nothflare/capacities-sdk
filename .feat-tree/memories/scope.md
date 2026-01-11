# Scope

**This IS:** Unofficial Python SDK providing full CRUD access to Capacities.io via reverse-engineered internal APIs, with MCP server for AI agent integration.

**Status:** COMPLETE - All features implemented, QoL refactor done

## Architecture

**SDK (capacities_sdk/):**
- `client.py` (257 lines) — Core HTTP client, inherits from 8 mixins
- `mixins/` — 8 domain-focused modules (objects, tasks, links, collections, bulk, export, graph, official)
- `models.py` — Object, Task, Space, Structure, GraphNode dataclasses
- `blocks.py` — Markdown parsing, block creation
- `exceptions.py` — Custom error types

**MCP Server (capacities_mcp/):**
- `server.py` (500 lines) — FastMCP with 8 action-based tools
- Server instructions explain Capacities domain model
- CAPACITIES_SPACE_ID auto-fills space_id in all tools

## Capabilities

- Full CRUD on any object type
- Task management (create, complete, priorities, due dates)
- Markdown auto-parsing to blocks (headings, code, lists, quotes)
- Find-replace content editing (old_string/new_string)
- Link creation and backlink discovery
- Collection management
- Full-text content search
- Bulk operations (create, update, delete, clone)
- Export/import (JSON backup, markdown export, restore)
- Graph traversal (1-3 levels)
- 8 MCP tools with 36 total actions
- 44 SDK methods across 8 mixins

## This is NOT

- Official/supported API client (could break if Capacities changes internals)
- Real-time sync client (no WebSocket/live updates)
- Full CRDT implementation (we sync whole entities, not incremental ops)
- Multi-user collaboration tool (designed for single-user personal access)

## Summary

| Component | Before Refactor | After Refactor |
|-----------|-----------------|----------------|
| client.py | 2290 lines | 257 lines |
| Mixins | 0 | 8 |
| MCP tools | 35 | 8 (36 actions) |
| server.py | 1430 lines | 500 lines |
| Framework | raw MCP SDK | FastMCP |
