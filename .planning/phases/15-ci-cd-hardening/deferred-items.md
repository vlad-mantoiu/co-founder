# Deferred Items from Phase 15 Plan 01

## Pre-existing Test Failures (Out of Scope)

These failures existed before Plan 01 execution and are NOT caused by marker changes.
Confirmed by git stash verification.

### 1. `tests/api/test_auth.py::TestRequireAuth::*` (4 failures)
- **Root cause:** `require_auth()` signature changed to include `request: Request` parameter, but these tests still call `require_auth(credentials=creds)` without `request`.
- **Fix needed:** Update test calls to pass a mock `Request` object, or use dependency injection pattern.

### 2. `tests/domain/test_usage_counters.py::*` (8 failures)
- **Root cause:** `UsageTracker` implementation doesn't match what tests expect. Tests check counter increments and TTL settings but the underlying `app.queue.usage.UsageTracker` appears to not implement the expected Redis key pattern.
- **Fix needed:** Review `UsageTracker` implementation against test expectations.

### 3. `tests/domain/test_runner_protocol.py::test_runner_is_runtime_checkable` (1 failure)
- **Root cause:** `Runner` protocol's `isinstance` check fails because it's not `@runtime_checkable` or missing some method in the test's `CompleteRunner` class.
- **Fix needed:** Add `@runtime_checkable` to `Runner` protocol or update test.

### 4. `tests/domain/test_runner_fake.py::test_happy_path_generate_brief_returns_brief`, `test_happy_path_generate_artifacts_returns_artifacts` (2 failures)
- **Root cause:** `RunnerFake.generate_brief()` and `generate_artifacts()` return values don't match what tests expect.
- **Fix needed:** Update RunnerFake responses or test expectations.

### 5. `tests/domain/test_artifact_models.py::TestArtifactTypeEnum::test_artifact_type_enum_has_five_values` (1 failure)
- **Root cause:** `ArtifactType` enum no longer has exactly five values that test expects.
- **Fix needed:** Update test to match current enum values.

**Total: 16 pre-existing failures deferred to future work.**
