# Risks

**"It failed because..."**

1. **Capacities changed internal API** — Watch for: HTTP 500 errors, inputValidationFailed responses, new required fields
2. **Auth tokens expired/changed format** — Watch for: 401 errors, token format changes in app updates
3. **Rate limiting introduced** — Watch for: 429 errors, slower responses, IP blocks
4. **Entity schema changed** — Watch for: Missing fields in responses, new required properties
5. **Web Worker sync moved to different endpoint** — Watch for: /content/syncing returning 404
6. **Link storage format changed** — Watch for: LinkTokens no longer in content blocks, linkNodes array populated

**Mitigations:**
- SDK has explicit error handling for each failure mode
- handoff.md documents exact working payload formats
- Feature Tree tracks which endpoints are used by which features
- Version pinning: appversion header locked to "web-1.57"
- Research file documents all discovered entity schemas

**Known Quirks:**
- Portal API uses `auth-token` header; Public API uses `Authorization` header
- Task status/priority are arrays: `["done"]` not `"done"`
- Links stored as LinkToken in content blocks, NOT in linkNodes array
- EntityBlocks use `entity.id` for target, not a separate field

**Recovery Plan:**
If sync breaks:
1. Check browser DevTools for current working payload
2. Compare to SDK's payload format
3. Update _sync_entity() method
4. Test with single object before batch

If links break:
1. Check IndexedDB for current link token format
2. Update LinkNode.from_link_token() and create_link_token()
3. Verify Object.get_links() still finds links

If auth breaks:
1. Check network requests for new header format
2. Update _request() method with new auth mechanism
3. Document in decisions.md
