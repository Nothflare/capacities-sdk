# Workflows

> Auto-generated. Do not edit. Use Claude Code to modify.

## CRUD.object_lifecycle
**Object Lifecycle Management**
*Enable AI agents and scripts to create, read, update, and delete objects in Capacities*
Complete CRUD workflow for managing Capacities objects programmatically

- **Status:** planned
- **Depends on:** SDK.write, SDK.read, SDK.official
- **Steps:**
  1. 1. Authenticate with auth token from Capacities settings
  2. 2. Get space ID and structure IDs via get_spaces() and get_structures()
  3. 3. CREATE: Use create_object() with structure_id, title, content
  4. 4. READ: Use get_object() or get_objects_by_ids() to fetch content
  5. 5. UPDATE: Use update_object() to modify title, content, tags
  6. 6. DELETE: Use delete_object() to move to trash
  7. 7. RESTORE: Use restore_object() to recover from trash

## DISCOVERY.explore_space
**Space Discovery**
*Allow users to browse all objects, filter by type, and search for specific content*
Explore and understand the contents of a Capacities space

- **Status:** planned
- **Depends on:** SDK.read, SDK.search, SDK.official
- **Steps:**
  1. 1. List all spaces with get_spaces()
  2. 2. Get structure definitions with get_structures(space_id)
  3. 3. List all objects with list_space_objects(space_id)
  4. 4. Filter by type with get_objects_by_structure(space_id, type)
  5. 5. Search by title with search_by_title(space_id, query)
  6. 6. Fetch full content with get_object(object_id)

## GRAPH.trace_connections
**Graph Exploration**
*Understand relationships and context by following links between objects*
Trace and visualize connections between objects in the knowledge graph

- **Status:** planned
- **Depends on:** SDK.graph, SDK.read
- **Steps:**
  1. 1. Start with a known object ID
  2. 2. Call trace_graph(object_id, max_depth=2) to follow links
  3. 3. Get summary with get_graph_summary() for stats and structure
  4. 4. Iterate through returned GraphNodes to explore connections
  5. 5. Fetch full content of connected objects as needed

## MCP.agent_integration
**AI Agent Integration**
*Enable Claude and other AI agents to fully interact with Capacities knowledge base*
Connect AI agents to Capacities via MCP server

- **Status:** planned
- **Depends on:** MCP.tools_read, MCP.tools_write
- **Steps:**
  1. 1. Set CAPACITIES_AUTH_TOKEN environment variable
  2. 2. Start MCP server: python -m capacities_mcp.server
  3. 3. Configure MCP client to connect to server
  4. 4. Use 13 available tools for CRUD, search, and graph operations
  5. 5. AI can now read/write/organize Capacities content
