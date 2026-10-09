# PHASE PULSE beta

Status: one genuine hosted Target shipping check PASSED; the second was rejected with HTTP 435 and a CAPTCHA indicator. Consistent monitoring is NOT verified. Schedule remains PAUSED.

## Latest Target-only result — October 8, 2026, 8:15 PM CDT

- Existing watchlist: 1 Target TCIN, 95120834 (Pokémon Mega Evolution Ascended Heroes Booster Bundle).
- Direct request to the existing `product_fulfillment_and_variation_hierarchy_v1` source removed the unnecessary product-metadata lookup dependency. No fingerprint, cookie, proxy, credential or access-protection changes.
- Check 1 PASS: HTTP 200, matching TCIN, `shipping_options.availability_status=OUT_OF_STOCK`, normalized `out_of_stock`, timestamp `2026-10-09T01:15:10.406500+00:00` (8:15:10 PM CDT). Product URL and prior metadata retained from the successful saved baseline. The price is historical metadata, not a freshly verified price.
- Check 2 FAIL: HTTP 435 with a CAPTCHA indicator at `2026-10-09T01:15:19.623544+00:00`. Requests stopped immediately; no third attempt.
- Two consecutive hosted checks: FAIL. No schedule activation and no new Discord webhook tests.
- Exact evidence saved under `direct_shipping_checks` in `verification.json`; production inventory baseline and configuration remain unchanged.
- Run: https://github.com/brickwolfpack-a11y/phase-pulse-beta/actions/runs/37868846468
- The existing Travis-ML backup uses the same Redsky fulfillment source; switching to it would not establish an independent supported source. Its browser-impersonation approach was not adopted. No supported alternative public inventory feed was established by the focused source review.
- Best next action: obtain a supported Target feed through the existing dedicated-provider trial inquiries (Zephyr/Moonitor), or approved retailer API access. Preserve the working Discord delivery and do not retry the challenged source or move it to another network to evade screening.



## Earlier verification — October 8, 2026, 8:10 PM America/Chicago

| Check | Result | Evidence |
| --- | --- | --- |
| Discord Target TEST | PASS | Message 1557922652516122640 in existing channel 1557676686143656007 |
| Discord Walmart TEST | PASS | Message 1557922671851737169 in existing channel 1557676779651473448 |
| Hosted Target inventory | FAIL | Search returned HTTP 200 and 24 records at 01:08 UTC; subsequent product-detail request returned HTTP 435 at 01:10 UTC. Search alone is not fulfillment verification. |
| Hosted Walmart inventory | FAIL | HTTP 412; response contains a CAPTCHA indicator. Requests stopped; no bypass attempted. |
| Duplicate prevention | PASS (controlled) | Baseline + unchanged state produce zero events; simulated OOS to in-stock produces one event; two unchanged observations produce zero more events; repeat delivery sends nothing. |
| Scheduled automatic monitoring | FAIL / paused | PULSE_ENABLED remains false. Two manually dispatched jobs ran independently, but no successful scheduled inventory run is established. |
| Genuine restock observed | NO | Both new Discord messages explicitly say TEST ONLY and simulated transition. |

Exactly one TEST message was sent per existing GitHub-configured retailer webhook, at 8:08 PM CDT. Returned Discord channel IDs matched, and both messages were visually confirmed in the PHASE channels. The second manual verification retained the saved delivery evidence without resending either message or retrying Walmart.

Production `state.json`, `report.json`, configuration, monitor code and scheduled workflow were unchanged. Test state is isolated in `verification.json`; original local inventory baseline remains preserved. No purchases or personal bot access.

Verification runs:
- https://github.com/brickwolfpack-a11y/phase-pulse-beta/actions/runs/37868291042
- https://github.com/brickwolfpack-a11y/phase-pulse-beta/actions/runs/37868444906

Next: resolve supported hosted inventory access, then complete two successful genuine checks per retailer and verify unchanged inventory produces no duplicate alerts. Only after those checks pass should the schedule be enabled and the next scheduled state commit verified. Do not repeatedly dispatch diagnostic requests after the saved rejection.

Supported-source investigation: Walmart Marketplace inventory APIs manage seller inventory, while Scintilla Store Inventory is supplier-scoped and reports items not mapped to the supplier as errors. Neither establishes an available free consumer-wide Target/Walmart feed for this project. No supported public Target inventory API access was verified. Sources: https://developer.walmart.com/global-marketplace/docs/inventory-api-overview and https://developer.walmartdataventures.com/apis/reference/nrt-store-inventory-details .

Run `python3 pulse.py check` from the repository root. Python 3.11+ standard library only: no npm install, browser runtime, personal bot session, proxy, or retailer account required.

## Evidence from October 8, 2026 (America/Chicago)

- Target: one known Pokémon Ascended Heroes booster-bundle TCIN (95120834), genuine product identity and shipping fulfillment retrieved; out of stock. Last successful baseline check 19:34:08 CDT.
- Walmart: five keyword searches returned 271 records before deduplication and filtering. 24 matching Walmart.com-sold products had explicit availability; 18 in stock. Last successful baseline check 19:34:45 CDT.
- A search result is not a completed checkout or proof of deliverability to every ZIP. Target store 1375 resolves to Minneapolis, not Chicago as the upstream comment claimed. This beta reports shipping availability, not Houston local pickup.
- Pokémon, One Piece, Panini, Topps and Funko keyword searches configured. Configuration does not imply that every category produced a matching first-party item.
- Zero genuine stock-change events observed during baseline; zero Discord messages sent.

## Earlier deployment checkpoint — before Discord verification

- Repository, Python monitor, tests, persistent inventory state and workflow saved.
- Existing Target and Walmart Discord webhooks stored as encrypted Actions secrets `DISCORD_TARGET_WEBHOOK_URL` and `DISCORD_WALMART_WEBHOOK_URL`; no channels or webhooks duplicated.
- First manually dispatched GitHub-hosted run: https://github.com/brickwolfpack-a11y/phase-pulse-beta/actions/runs/37867059374 . All 10 unit tests passed, but the actual retailer checks failed at 00:53:47 UTC: Target HTTP 435; Walmart HTTP 412. Those status codes alone do not establish the underlying cause.
- `report.json` and the preserved baseline were committed by the workflow. Zero stock-change alerts or verification messages were delivered.
- Repository variable `PULSE_ENABLED=false` was saved after this failure. The 15-minute cron remains defined (UTC minutes 7, 22, 37 and 52), but inventory jobs are paused. Do not re-enable merely to retry these rejected endpoints.
- The hosted job proves execution independent of the user's computer, but does NOT prove functioning hosted inventory retrieval or Discord delivery. This beta is NOT LIVE.
- Last genuine successful checks remain the local baseline: Target 2026-10-09 00:34:08 UTC (1 product); Walmart 00:34:45 UTC (24 products, 18 explicitly in stock at that time). These are historical observations, not current stock promises.

### Required next steps

1. Resolve supported retailer access or obtain an authorized dedicated monitor feed before re-enabling inventory requests. No proxy, personal-token, CAPTCHA, fingerprint or network-path bypass.
2. After access is resolved, pass a fresh genuine hosted inventory check, verify correctly labeled delivery into each existing Discord channel, and observe a scheduled run. A simulated webhook message does not establish monitoring.
3. Preserve existing state and review pending/reserved/uncertain events before resuming to avoid duplicate notifications. Never upload an older baseline over newer workflow state.
4. GitHub scheduling can be delayed; this remains a beta. No paid hosting or provider subscription has been purchased.

## Correctness and safety

- Target uses product-specific shipping fulfillment, not presence/absence in a capped search page. Product IDs must match the response.
- Walmart requires sellerName exactly Walmart.com and explicit availability. Unknown inventory is never classified as out of stock.
- Newly discovered items silently baseline. Restock alerts require a previously unavailable/preorder item to become explicitly in stock. Preorders stay distinct.
- Missing search items retain their previous observation timestamp and are NOT marked recently checked or out of stock.
- Retailer errors preserve previous state. HTTP 401/403/429 or an access challenge persistently pauses that retailer until deliberate review; no automatic blocked-endpoint retries.
- Search scope is one page per term. Walmart items absent from those pages are stale, not continuously verified. Target watchlist starts with one known product and can expand through first-party discovery (up to 12 checks per run).
- State is committed to git before notifications. Per-run delivery reservations are committed before webhook calls. A rerun has a distinct reservation token; ambiguous deliveries are held for review, not replayed. This favors avoiding duplicates over guaranteed delivery in a crash. Review reserved/uncertain events manually.
- Notifications are sent with `wait=true`, retaining the returned Discord message ID. Mentions are disabled. Events older than 15 minutes expire.
- Per-retailer errors and last successful timestamps appear in `report.json` and the Actions job summary. A failed inventory check marks the workflow failed. Discord health alerts are not yet configured.
- Existing state must never be deleted to force a fresh run. Missing state silently baselines without alerting.

## Source review

Primary: pranavtallapaka/pokemon-restock at 68c4219048645385aa426d3ea6763f6c0017a9fd. README declares MIT. Its Walmart JSON extraction/seller filtering and Target API approach informed this adaptation. Original Node dependencies include axios, cheerio, dotenv, express, node-cron and nodemailer; the lockfile advisory lookup flagged vulnerable packages. They are not installed or executed by the beta.

Material upstream issues addressed: hardcoded Pokémon search terms ignore environment configuration; Target's failed/truncated in-stock pass can yield false OOS; Walmart can infer stock from an ATC control and maps unknown to OOS; blocked Walmart pages can be followed by additional keyword requests; default workflow enables unrelated retailers/community feeds and includes an unrelated user mention; a single webhook does not route two retailer channels separately; state could advance after failed notification delivery.

Backup: XanderRobbins/GianPokemonTracker at c29cb7a0774ad0cacbabcf10ee743def29b15bcf. Python dependencies include requests, BeautifulSoup, PyYAML, Playwright, Flask, pywebview and PyInstaller with lower bounds rather than a lockfile. Target checker expects fulfillment in a PDP response where live testing found it absent. Walmart discovery retries fresh browser contexts after blocks, contrary to the requested no-bypass policy. Not executed.

Backup: Travis-ML/target-stock-monitor at 0bcab33d5a37b8a2b17b066e81ed725e2b931a06. MIT license retained in LICENSE-Target-source. Its product-specific Target fulfillment approach is used, with validated public frontend key and strict classification. Original requires requests and uses process-memory state, a start notification, and a CLI webhook argument; not suitable unchanged for persistent secret-safe operation. No Walmart adapter.

Only the reviewed Python entry point is used for beta execution. No personal bot account, subscription, support-server feed, authentication token or private bot configuration is involved.
