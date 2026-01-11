# Capacities SDK - Project Context

## What Is This?

Unofficial Python SDK and MCP server for Capacities.io (graph-based PKM app). Provides full CRUD access via reverse-engineered internal APIs since the official API lacks basic read functionality.

## What is Capacities?

Capacities.io is a graph-based Personal Knowledge Management (PKM) application where **everything is an Object**.

### Core Concepts

- **Objects**: The fundamental unit. Everything is an object - notes, pages, people, books, custom types
- **Structures**: Object types/schemas. Built-in (RootPage, RootDailyNote, RootTag) or custom (UUID-based)
- **Properties**: Fields on objects - title, description, tags, custom properties
- **Blocks**: Content within objects - TextBlock, CodeBlock, HeadingBlock, TableBlock
- **Links**: Connections between objects stored in `linkNodes` array
- **Collections/Databases**: Groups of objects for organization

### API Architecture

| API | Base URL | Purpose | Auth |
|-----|----------|---------|------|
| Internal Portal | portal.capacities.io | Full CRUD, used by web app | auth-token: Bearer JWT |
| Official Public | api.capacities.io | Limited, documented | Authorization: Bearer JWT |

### Key Endpoints

**Internal (Reverse Engineered):**
- `POST /content/syncing` - Create/Update/Delete objects
- `POST /content/id-list` - Get objects by IDs (full content)
- `POST /content/space-content` - List all objects in space
- `GET /content/trash/{spaceId}` - Trashed items

**Official:**
- `GET /spaces` - List spaces
- `GET /space-info` - Get structures
- `POST /lookup` - Search by title
- `POST /save-weblink` - Save URL
- `POST /save-to-daily-note` - Add to daily note

### Sync Payload Format

```json
{
  "syncClientId": "<uuid>",
  "elements": [{
    "spaceId": "<space-uuid>",
    "content": {
      "id": "<object-uuid>",
      "type": "RootEntity",
      "structureId": "<structure-uuid>",
      "properties": { "title": {"val": "..."} },
      "data": { "blocks": {...} },
      "deleteRequested": false,
      ...
    }
  }]
}
```

## Key Assumptions

- [validated] Internal sync API accepts elements format with full entity — tested and working
- [validated] Auth token from desktop app works for internal API — tested and working
- [untested] API will remain stable across Capacities updates — watch for breaking changes
- [untested] Rate limits are generous for automation use — no documented limits found
- [untested] linkNodes can be modified for link creation — schema found but not tested

## Project Structure

```
capacities_sdk/
  __init__.py      # Package exports
  client.py        # CapacitiesClient with all CRUD methods
  models.py        # Object, Block, Property, GraphNode dataclasses
  exceptions.py    # Custom error types

capacities_mcp/
  __init__.py
  server.py        # MCP server with 13 tools

.feat-tree/
  plans/           # Enhancement plans
  memories/        # User, scope, risks, decisions
```

## Critical Files for Development

| File | Purpose |
|------|---------|
| `.feat-tree/research/complete-findings.md` | **READ FIRST** - All API research, schemas, payloads |
| `.feat-tree/plans/sdk-enhancements.md` | Enhancement plan with implementation details |
| `.feat-tree/memories/handoff.md` | Session handoff with progress and decisions |

## For Future Development

### To Add a New Feature:
1. Use Chrome MCP to intercept the action in Capacities web app
2. Capture exact payload format from network requests
3. Test payload via JavaScript in browser console
4. Implement in `capacities_sdk/client.py`
5. Add MCP tool in `capacities_mcp/server.py`
6. Update Feature Tree status from planned to active

### Testing Values:
See `.secrets.env` (gitignored) for:
- `CAPACITIES_AUTH_TOKEN` — Portal API auth token
- `CAPACITIES_SPACE_ID` — Test space UUID
- `CAPACITIES_NOTE_STRUCTURE_ID` — Note structure UUID

### Common Errors:
- `inputValidationFailed` — Payload format wrong, compare to working example
- `401` — Token expired, get new one from Settings > Capacities API
- `404` — Endpoint changed, check browser network tab for current URL
