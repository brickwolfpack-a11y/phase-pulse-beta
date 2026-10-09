# PHASE PULSE beta

Status: baseline verified locally; cloud deployment and Discord delivery not yet verified.

Run `python3 pulse.py check` from the repository root. Python 3.11+ standard library only: no npm install, browser runtime, personal bot session, proxy, or retailer account required.

## Evidence from October 8, 2026 (America/Chicago)

- Target: one known Pokémon Ascended Heroes booster-bundle TCIN (95120834), genuine product identity and shipping fulfillment retrieved; out of stock. Last successful baseline check 19:34:08 CDT.
- Walmart: five keyword searches returned 271 records before deduplication and filtering. 24 matching Walmart.com-sold products had explicit availability; 18 in stock. Last successful baseline check 19:34:45 CDT.
- A search result is not a completed checkout or proof of deliverability to every ZIP. Target store 1375 resolves to Minneapolis, not Chicago as the upstream comment claimed. This beta reports shipping availability, not Houston local pickup.
- Pokémon, One Piece, Panini, Topps and Funko keyword searches configured. Configuration does not imply that every category produced a matching first-party item.
- Zero genuine stock-change events observed during baseline; zero Discord messages sent.

## Deployment (not completed)

1. Create or reuse one PHASE repository. Public standard GitHub-hosted runners avoid private-repository minute charges; code and retailer stock state may be public, never credentials.
2. Push this reviewed revision. Only `.github/workflows/monitor.yml` is scheduled; it runs the Python beta rather than the upstream Node program.
3. Store the EXISTING channel webhook URLs as repository Actions secrets `DISCORD_TARGET_WEBHOOK_URL` and `DISCORD_WALMART_WEBHOOK_URL`. Do not make replacement channels or webhooks. Do not put secrets in code, state, artifacts, command arguments or logs.
4. Set repository variable `PULSE_ENABLED=true` only after secrets and configuration are verified. Dispatch a manual run, inspect live retailer evidence on the hosted runner, then observe a scheduled run.
5. Schedule: UTC minutes 7, 22, 37 and 52. GitHub may delay or drop scheduled jobs; this is a beta, not a latency guarantee. The cloud job does not require the user's computer to remain on. This independence must still be verified by an actual hosted run.

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
