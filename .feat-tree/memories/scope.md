# Scope

**This IS:** Unofficial Python SDK providing full CRUD access to Capacities.io via reverse-engineered internal APIs, with MCP server for AI agent integration.

**Status:** COMPLETE - All planned features implemented

**Capabilities:**
- Full CRUD on any object type
- Task management (create, complete, priorities, due dates)
- Markdown auto-parsing to blocks (headings, code, lists, quotes)
- Link creation and backlink discovery
- Collection management
- Full-text content search
- Bulk operations (create, update, delete, clone multiple objects)
- Export/import (JSON backup, markdown export, restore from backup)
- Graph traversal
- 35 MCP tools for AI agents
- 44 SDK methods

**This is NOT:**
- Official/supported API client (could break if Capacities changes internals)
- Real-time sync client (no WebSocket/live updates)
- Full CRDT implementation (we sync whole entities, not incremental ops)
- Multi-user collaboration tool (designed for single-user personal access)
- Mobile/web client (Python SDK only)

**Features we said no to:**
- **WebSocket real-time sync**: Too complex, not needed for automation use case
- **Incremental CRDT operations**: Full entity sync is simpler and works
- **Offline-first with conflict resolution**: Server is source of truth
- **Browser automation fallback**: Internal API works, no need for UI automation
- **Official API expansion wait**: User needs access now, not "when they add endpoints"

**SDK Summary:**
| Category | Methods | MCP Tools |
|----------|---------|-----------|
| Read | 4 | 7 |
| Write | 4 | 6 |
| Tasks | 12 | 7 |
| Collections | 4 | 3 |
| Search | 2 | 1 |
| Links | 4 | 4 |
| Graph | 2 | 1 |
| Bulk | 5 | 4 |
| Export | 3 | 3 |
| Official | 4 | - |
