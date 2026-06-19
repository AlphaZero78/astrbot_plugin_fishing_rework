# Migration Plan

1. Preserve the current runnable behavior in a clean standalone repository.
2. Remove fork-specific repository metadata while retaining required license
   and attribution notices.
3. Convert mechanics into pure, testable calculation modules.
4. Move defaults and editable values into one validated configuration system.
5. Expose runtime configuration and item-effect payloads through the WebUI.
6. Build expected-value tooling before changing zone, equipment, bait, shop,
   and gacha values.
7. Apply explicit database migrations for all identifier or schema changes.
8. Run the complete migration, mechanics, WebUI, concurrency, and dual-instance
   test matrix before replacing the existing plugin deployment.
