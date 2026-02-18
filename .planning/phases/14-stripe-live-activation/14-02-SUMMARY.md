---
phase: 14-stripe-live-activation
plan: 02
subsystem: testing
tags: [stripe, billing, pytest, async, idempotency, webhook, tdd]

# Dependency graph
requires:
  - phase: 14-01
    provides: billing.py with idempotency, async SDK, and startup validation

provides:
  - "12-test billing API suite covering BILL-01, BILL-02, BILL-03"
  - "Webhook idempotency verification (duplicate event_id returns 200 and skips)"
  - "Async SDK assertion tests (create_async called, not sync create)"
  - "validate_price_map() unit tests for all three cases"
  - "Payment failure downgrade integration test via direct handler invocation"

affects:
  - "14-03 (Stripe webhook registration)"
  - "14-04 (E2E smoke test)"
  - "15-ci-cd"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "stripe.SignatureVerificationError raised (not generic Exception) in webhook signature mocks"
    - "_handle_payment_failed unit-tested directly to avoid sync/async event-loop conflicts with TestClient"
    - "AsyncMock used for stripe.*.create_async assertions"
    - "Separate engine fixture for async handler tests that need isolated DB setup"

key-files:
  created:
    - backend/tests/api/test_billing_api.py
  modified: []

key-decisions:
  - "Use stripe.SignatureVerificationError (not generic Exception) in mock to trigger correct 400 handler path"
  - "Unit-test _handle_payment_failed directly via patched session factory — avoids asyncio event-loop conflict with sync TestClient"
  - "Async payment-failure test creates its own isolated DB engine/factory to avoid fixture scope conflicts"
  - "os.environ.setdefault() at module level sets dummy STRIPE_PRICE_* env vars to prevent conftest api_client startup failures"

patterns-established:
  - "Billing webhook tests: patch stripe.Webhook.construct_event with return_value=fake_event dict"
  - "Async SDK tests: patch stripe.*.create_async with AsyncMock and assert_called_once()"
  - "Startup validation tests: patch app.main.get_settings with MagicMock controlling debug flag and price ID values"
  - "Payment handler direct tests: patch app.api.routes.billing.get_session_factory with test-scoped factory"

requirements-completed: [BILL-01, BILL-02, BILL-03]

# Metrics
duration: 4min
completed: 2026-02-19
---

# Phase 14 Plan 02: Billing API Tests Summary

**12-test TDD suite verifying webhook idempotency (BILL-01), async Stripe SDK calls (BILL-03), and startup price-map validation (BILL-02) against the hardened billing.py from Plan 01**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-19T20:15:01Z
- **Completed:** 2026-02-19T20:19:00Z
- **Tasks:** 1 (TDD: RED + GREEN in single pass since implementation existed from 14-01)
- **Files modified:** 1

## Accomplishments

- 12 tests across 4 test classes, all passing
- Webhook idempotency verified: first event processes, duplicate returns 200 and skips handler
- Stripe async SDK verified: `checkout.Session.create_async`, `billing_portal.Session.create_async`, `Customer.create_async` all asserted via `AsyncMock`
- `validate_price_map()` tested for all three cases: raises on missing (prod), skips in debug, passes when all set
- Payment failure downgrade tested via direct `_handle_payment_failed()` invocation with isolated test engine

## Task Commits

1. **Task 1: Billing API test suite (TDD GREEN)** - `e480417` (test)

**Plan metadata:** (created in this message)

## Files Created/Modified

- `backend/tests/api/test_billing_api.py` — 12 tests: TestWebhookIdempotency (4), TestAsyncStripeSDK (3), TestValidatePriceMap (3), TestPaymentFailure (2)

## Decisions Made

- Used `stripe.SignatureVerificationError` (not generic `Exception`) in the invalid-signature mock — billing.py only catches `ValueError` and `SignatureVerificationError` specifically; generic Exception would propagate as 500
- Unit-tested `_handle_payment_failed` directly instead of via HTTP to avoid `asyncio.get_event_loop().run_until_complete()` conflicts with the sync TestClient's event loop
- Async payment-failure test creates its own DB engine and session factory (independent of conftest engine) for full isolation

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Invalid signature mock raised wrong exception type**
- **Found during:** Task 1 (initial test run)
- **Issue:** Test used `side_effect=Exception("bad sig")` but billing.py only catches `stripe.SignatureVerificationError`. Generic Exception propagated as 500, not 400.
- **Fix:** Changed to `side_effect=stripe.SignatureVerificationError("Invalid signature", "t=0,v1=bad")`
- **Files modified:** backend/tests/api/test_billing_api.py
- **Verification:** Test now passes with status_code 400 as intended
- **Committed in:** e480417 (Task 1 commit)

**2. [Rule 1 - Bug] Event-loop conflict in mixed async/sync payment failure test**
- **Found during:** Task 1 (initial test run)
- **Issue:** `asyncio.get_event_loop().run_until_complete()` called inside a sync test method that already ran inside pytest-asyncio's event loop — "Task got Future attached to a different loop"
- **Fix:** Restructured to async test method that directly invokes `_handle_payment_failed()` with a patched session factory backed by a fresh test engine
- **Files modified:** backend/tests/api/test_billing_api.py
- **Verification:** All 12 tests pass in 1.72s
- **Committed in:** e480417 (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — bug in test code itself)
**Impact on plan:** Both fixes necessary for test correctness. No scope creep.

## Issues Encountered

None beyond the two auto-fixed deviations above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Billing test suite complete — BILL-01, BILL-02, BILL-03 all verified
- Ready for 14-03: Stripe webhook URL registration (operational step post-deploy)
- Ready for 14-04: E2E smoke test for checkout flow

---
*Phase: 14-stripe-live-activation*
*Completed: 2026-02-19*
