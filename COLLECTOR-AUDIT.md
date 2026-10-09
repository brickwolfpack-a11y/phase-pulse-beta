# Target collector audit — 2026-10-09 UTC

This branch remains paused. No retailer request, webhook post, or host migration was performed during this audit. All 27 local tests pass; seven new tests are offline regressions, not live monitoring evidence.

## Compared implementations

| Source snapshot | Target request and environment | Evidence and limitation |
|---|---|---|
| pranavtallapaka/pokemon-restock 68c4219 | Node >=18 / Axios, GitHub Actions; Redsky plp_search_v2, paginated all-products and purchasable-products search passes | README acknowledges intermittent bot blocking. Shipping availability is NOT independently verified: absence from the limited filtered pass becomes out_of_stock. Errors break pagination and can make incomplete results look valid. EXTRA_KEYWORDS is declared but unused. No fresh upstream hosted success was established. |
| XanderRobbins/GianPokemonTracker c29cb7a | Python requests; Redsky pdp_client_v1; configured TCIN, store and public frontend key | README explicitly reports Target CAPTCHA failures, including visible browser tests, reverified 2026-08-22. It does not offer an independent accessible Target feed. Its boolean parser treats missing/unrecognized availability as false; PHASE retains unknown instead. Playwright dependencies support other retailers, not a working Target fix. |
| Travis-ML/target-stock-monitor 0bcab33 | Python requests; Redsky product_fulfillment_and_variation_hierarchy_v1 | Same fulfillment source PHASE already uses. README says supplied API key must be replaced. No proven independent GitHub Actions success. Browser-like headers and is_bot=false are not adopted as access workarounds. |
| PHASE feature/target-discovery | Python standard library; separate search metadata and explicit shipping availability; GitHub Actions Ubuntu | Recorded genuine OUT_OF_STOCK for TCIN 95120834 once; subsequent same-source request HTTP 435 with CAPTCHA. Not reliable or active. |

## Request and failure analysis

The saved hosted diagnostic used the same frontend key, TCIN 95120834, store 1375, ZIP 55403, WEB channel, page /p/A-95120834, visitor identifier and honest PHASE User-Agent for both iterations. Its first shipping response was HTTP 200 at 2026-10-09T01:15:10.406500+00:00; the next check began 2026-10-09T01:15:19.623544+00:00 and returned HTTP 435 / application/json with a CAPTCHA signal. Evidence is retained in verification.json under direct_shipping_checks (run 37868846468-1).

This establishes that the identifier, request and shipping path worked once, followed by a server-side access challenge before inventory parsing. It does NOT reveal the security system's exact trigger. IP reputation, frequency, session requirements and header scoring cannot be distinguished from these logs; claiming a specific cause or promising a delay/header fix would be speculation. There is no evidence here of a TCIN typo, rotated-key error, or parser causing HTTP 435. The configured ZIP is the inventory destination context; results are not a guarantee for every customer's ZIP.

All three implementations depend on the same Redsky service. Copying another endpoint/client, modifying identity headers, adding cookies, solving CAPTCHA automatically, or switching network routes is not a verified permitted fix. Upstream README claims/sample logs are not PHASE live checks. We have not run the original scraper against the already-blocked service, so we do not claim a fresh observed failure of that exact executable.

## Concrete fixes in this change

- Ordinary discovery network/schema failures no longer prevent explicit saved-TCIN inventory checks. Discovery remains a complementary automatic input. Access/pause errors still immediately stop all Target traffic.
- Null/malformed shipping availability remains unknown; malformed product envelopes and TCIN mismatches become explicit retrieval errors rather than crashes or false out-of-stock.
- A successful known-product check with failed discovery is reported as partial, preserves inventory state and deduplication, and does not return overall healthy status.
- Seven regressions verify separation, challenge stop, null status, malformed envelopes, identity checks, persisted unchanged inventory and the recorded genuine observation/block evidence. No Discord setup/test was repeated.

## Exact next technical step

No alternative accessible independent Target stock source was verified in these repositories. Code changes above repair collection robustness but cannot remove the server-side restriction. Before another live test, establish a documented permitted Target access method or explicit source access resolution. Then use the existing shipping parser for one saved TCIN, a small discovered set, two hosted checks, a fresh baseline and state persistence; only then remove pause flags and enable scheduling. No commercial-provider research or purchase was performed.
