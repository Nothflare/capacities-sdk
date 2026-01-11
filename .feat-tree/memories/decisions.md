# Design Decisions

**API Strategy:** Hybrid internal + official
- Considered: Internal only, Official only, Browser automation
- Chose because: Internal has full read/write, official has stable space/structure APIs
- Trade-off accepted: Depends on undocumented internal API that could change

**Sync Payload Format:** Elements array with full entity
- Considered: Components array, incremental operations, CRDT ops
- Chose because: Elements format worked on first successful test
- Trade-off accepted: Sends full entity even for small changes (bandwidth)

**Auth Mechanism:** auth-token header with Bearer prefix
- Considered: Authorization header, cookies, session tokens
- Chose because: Matches what web app actually uses (intercepted)
- Trade-off accepted: Token must be manually obtained from app settings
- Note: Portal API uses auth-token header; Public API uses Authorization header

**Delete Strategy:** Soft delete via deleteRequested flag
- Considered: Hard delete endpoint, separate trash API
- Chose because: Matches app behavior, allows restore
- Trade-off accepted: Objects remain in responses until trash emptied

**Block Support:** Full markdown with auto-parsing
- Considered: TextBlock only, manual block construction
- Chose because: AI agents pass markdown naturally, auto-parse to proper blocks
- Supported: HeadingBlock, CodeBlock, TextBlock (with lists, quotes), HorizontalLineBlock
- Trade-off accepted: Some advanced block types (tables, embeds) need manual construction

**Link Storage:** LinkTokens in content blocks, NOT linkNodes array
- Discovered: linkNodes array at entity level is always empty
- Reality: Links stored as LinkToken in TextBlock tokens, or EntityBlock for embeds
- Impact: Must parse content blocks to find links, add links by modifying blocks

**Task Properties:** Status/priority as single-element arrays
- Discovered: API uses `["done"]` not `"done"` for status
- Format: `status: {val: ["done"]}`, `priority: {val: ["high"]}`
- Date format: `{startTime: "ISO", dateResolution: "day"}`

**Fulltext Search:** Client-side fallback
- Primary: Try /resources/search endpoint
- Fallback: Fetch all objects and search locally
- Reason: Search endpoint may not be available or may have different auth

**MCP Over Direct Integration:**
- Considered: Direct Python library only, REST API server
- Chose because: User explicitly wanted AI agent access via MCP
- Trade-off accepted: Requires MCP client setup
