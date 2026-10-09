# Target discovery feature checkpoint

Branch: `feature/target-discovery`. Live polling remains paused.

## Source comparison and licensing

Reviewed `pranavtallapaka/pokemon-restock` at `68c4219048645385aa426d3ea6763f6c0017a9fd`: `scrapers/target.js`, `stateManager.js`, `monitor.js`, `notifier.js`, and the Discord notifier. Upstream README declares MIT; its root has no standalone license text. This change implements compatible concepts in the existing Python runtime rather than copying the JavaScript implementation or adding its dependencies. Existing source attribution and Travis-ML MIT license remain intact.

Adapted concepts: paged keyword discovery, TCIN-based identity, canonical product links, first-seen/last-seen tracking, initial silent baseline, distinct new-listing events and stock transitions, persistent deduplication. The upstream EXTRA_KEYWORDS constant is declared but not actually iterated by the reviewed scraper; PHASE now iterates configured terms with a bounded rotating request budget.

Not adopted: inferring out-of-stock from absence in a limited search pass; assuming missing marketplace flags mean Target-direct; refreshing last-seen for missing items; browser impersonation; adding cookie/proxy retries; unrelated retailers and notifications; automatic fresh state after corrupt JSON. Existing Python state parsing fails instead of silently losing history.

## Implementation

- `discovery.py` separates metadata discovery from shipping evidence. Keyword include/exclude and optional category-name filters are applied to actual response fields. No guessed category IDs or new endpoints.
- Default budget is two search requests per run. Existing one-page-per-term configuration is preserved; optional pagination is capped at three pages, and the cursor rotates fairly across terms/pages.
- Discovered products persist under `state.target.discovery.products` with first/last-seen timestamps. Missing results retain their old timestamp; errors retain completed pages and prior stock observations.
- Marketplace/unknown sellers remain identifiable in discovery history but are not automatically admitted to first-party shipping monitoring.
- Each query/page silently baselines once. A later unseen TCIN creates one persistent `new_listing` journal event. This means **new to the monitor**, not proof of the retailer's publication date. Expanding a query does not flood new-listing events.
- Discovery events do not enter the restock outbox or send Discord alerts. Dedicated new-listing notification delivery remains deferred until the live source is reliable; discovery alone cannot assert stock.
- Eligible discoveries automatically join the existing watchlist. Inventory checking rotates through a bounded number of products rather than always selecting the same first IDs.
- `pulse.check_target` uses saved/discovered metadata and the existing shipping fulfillment endpoint, avoiding the unnecessary PDP metadata dependency. Only explicit shipping status can update stock or generate an existing restock event.
- Existing durable delivery reservations and duplicate filtering remain unchanged. No webhook tests were repeated.
- Target HTTP 435 and Walmart HTTP 412 now join access-pause codes. Explicit configured pause reasons block both collectors before any network request. `PULSE_ENABLED` remains false and both existing workflow files are unchanged.

## Validation

20 local unittest tests pass: 10 original tests plus 10 discovery/integration tests covering URLs/TCIN identity, seller filters, category/exclude rules, persistence round-trip, new-listing deduplication, missing items, partial failures, request/page budgets, fair watchlist rotation, real-shipping-only classification and zero-request pause guards.

Offline replay of the previously saved genuine Target response found 24 unique relevant listings with valid Target URLs. All 24 were marketplace products: zero new Target-direct inventory candidates. Both initial baseline and unchanged replay produced zero notifications. These are historical replay results, not fresh discovery or live stock checks. Counts are in `discovery-validation.json`.

The prior genuine hosted check for TCIN 95120834 returned OUT_OF_STOCK at 2026-10-09 01:15:10 UTC. The following request returned HTTP 435 with a CAPTCHA indicator. No live retailer requests were made for this feature development.

## Remaining activation gate

Resolve supported source access; then verify fresh discovery and shipping for relevant first-party products, complete two successful hosted checks, and observe a scheduled state commit before declaring live. Walmart remains paused. New-listing journal events are implemented; independent new-listing Discord delivery is not yet enabled. Discovery architecture does not remove the access restriction.
