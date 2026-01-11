# Design Decisions

## Architecture

**Mixin Pattern for SDK:**
- Considered: Composition, separate service classes, single monolithic client
- Chose because: Keeps `client.method()` API unchanged, no breaking changes
- Trade-off accepted: Multiple inheritance (but Python handles this well)

**FastMCP for MCP Server:**
- Considered: Raw MCP SDK, custom framework
- Chose because: Clean decorators, dependency injection, automatic schema generation
- Trade-off accepted: Additional dependency

**8 Action-Based Tools (vs 35 separate):**
- Considered: One tool per operation, fewer mega-tools
- Chose because: Domain grouping is intuitive, reduces context window usage for AI
- Trade-off accepted: Slightly more complex tool schemas

## API Strategy

**Hybrid Internal + Official:**
- Considered: Internal only, Official only, Browser automation
- Chose because: Internal has full read/write, official has stable space/structure APIs
- Trade-off accepted: Depends on undocumented internal API that could change

**Auth Mechanism:** auth-token header with Bearer prefix
- Portal API uses `auth-token` header
- Public API uses `Authorization` header

## Content Handling

**Find-Replace for Update:**
- Considered: Full replace only, append mode, diff-based
- Chose because: Matches Edit tool UX, intuitive for Claude
- Implementation: old_string/new_string params do `.replace(old, new, 1)`

**Markdown Auto-Parsing:**
- Considered: Raw blocks only, manual construction
- Chose because: AI agents pass markdown naturally
- Supported: HeadingBlock, CodeBlock, TextBlock (lists, quotes), HorizontalLineBlock

## Configuration

**CAPACITIES_SPACE_ID Env Var:**
- Considered: Always require space_id, prompt selection, config file
- Chose because: Most users have one space, reduces friction
- Implementation: Server instructions tell Claude if configured

**Server Instructions:**
- Considered: Tool descriptions only, external docs
- Chose because: Claude needs domain context to use MCP confidently
- Content: Explains Objects, Structures, Links, Collections

## Data Model

**Sync Payload Format:** Elements array with full entity
- Chose because: Elements format worked on first successful test
- Trade-off accepted: Sends full entity even for small changes

**Delete Strategy:** Soft delete via deleteRequested flag
- Chose because: Matches app behavior, allows restore
- Trade-off accepted: Objects remain in responses until trash emptied

**Link Storage:** LinkTokens in content blocks, NOT linkNodes array
- Discovered: linkNodes array at entity level is always empty
- Reality: Links stored as LinkToken in TextBlock tokens, or EntityBlock for embeds

**Task Properties:** Status/priority as single-element arrays
- Format: `status: {val: ["done"]}`, `priority: {val: ["high"]}`
- Date format: `{startTime: "ISO", dateResolution: "day"}`
