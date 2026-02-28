"""Unit tests for error classification and signature hashing (AGNT-07).

Tests for:
- ErrorCategory enum values
- classify_error() categorization logic for all 3 categories
- build_error_signature() deterministic hashing
"""

import hashlib

import pytest

from app.agent.error.classifier import (
    ErrorCategory,
    build_error_signature,
    classify_error,
)


# ---------------------------------------------------------------------------
# ErrorCategory enum tests
# ---------------------------------------------------------------------------


class TestErrorCategory:
    def test_has_never_retry(self):
        assert ErrorCategory.NEVER_RETRY == "never_retry"

    def test_has_code_error(self):
        assert ErrorCategory.CODE_ERROR == "code_error"

    def test_has_env_error(self):
        assert ErrorCategory.ENV_ERROR == "env_error"

    def test_is_str_enum(self):
        assert isinstance(ErrorCategory.NEVER_RETRY, str)
        assert isinstance(ErrorCategory.CODE_ERROR, str)
        assert isinstance(ErrorCategory.ENV_ERROR, str)


# ---------------------------------------------------------------------------
# classify_error — NEVER_RETRY patterns
# ---------------------------------------------------------------------------


class TestClassifyErrorNeverRetry:
    def test_permission_denied(self):
        result = classify_error("PermissionError", "access denied to resource")
        assert result == ErrorCategory.NEVER_RETRY

    def test_authentication_failed(self):
        result = classify_error("AuthError", "authentication failed for user")
        assert result == ErrorCategory.NEVER_RETRY

    def test_unauthorized(self):
        result = classify_error("HTTPError", "unauthorized request")
        assert result == ErrorCategory.NEVER_RETRY

    def test_forbidden(self):
        result = classify_error("HTTPError", "forbidden: 403")
        assert result == ErrorCategory.NEVER_RETRY

    def test_invalid_credentials(self):
        result = classify_error("AuthError", "invalid credentials provided")
        assert result == ErrorCategory.NEVER_RETRY

    def test_rate_limit_exceeded(self):
        result = classify_error("RateLimitError", "rate limit exceeded for API")
        assert result == ErrorCategory.NEVER_RETRY

    def test_subscription(self):
        result = classify_error("BillingError", "subscription required to access")
        assert result == ErrorCategory.NEVER_RETRY

    def test_invalid_subscription(self):
        result = classify_error("BillingError", "invalid subscription tier")
        assert result == ErrorCategory.NEVER_RETRY

    def test_error_type_contains_pattern(self):
        # pattern in error_type field
        result = classify_error("Unauthorized", "some message")
        assert result == ErrorCategory.NEVER_RETRY

    def test_case_insensitive_matching(self):
        result = classify_error("Error", "ACCESS DENIED to directory")
        assert result == ErrorCategory.NEVER_RETRY


# ---------------------------------------------------------------------------
# classify_error — ENV_ERROR patterns
# ---------------------------------------------------------------------------


class TestClassifyErrorEnvError:
    def test_connection_refused(self):
        result = classify_error("ConnectionError", "connection refused on port 5432")
        assert result == ErrorCategory.ENV_ERROR

    def test_network_timeout(self):
        result = classify_error("TimeoutError", "network timeout after 30s")
        assert result == ErrorCategory.ENV_ERROR

    def test_timeout_alone(self):
        result = classify_error("TimeoutError", "operation timed out")
        assert result == ErrorCategory.ENV_ERROR

    def test_name_resolution_failed(self):
        result = classify_error("OSError", "name resolution failed for registry.npmjs.org")
        assert result == ErrorCategory.ENV_ERROR

    def test_disk_full(self):
        result = classify_error("OSError", "disk full: no space left on device")
        assert result == ErrorCategory.ENV_ERROR

    def test_no_space_left(self):
        result = classify_error("OSError", "no space left on device")
        assert result == ErrorCategory.ENV_ERROR

    def test_package_registry(self):
        result = classify_error("PackageError", "package registry unreachable")
        assert result == ErrorCategory.ENV_ERROR

    def test_registry_down(self):
        result = classify_error("InstallError", "registry down: npm.io")
        assert result == ErrorCategory.ENV_ERROR

    def test_temporary_failure(self):
        result = classify_error("DNSError", "temporary failure in name resolution")
        assert result == ErrorCategory.ENV_ERROR

    def test_service_unavailable(self):
        result = classify_error("HTTPError", "service unavailable: 503")
        assert result == ErrorCategory.ENV_ERROR


# ---------------------------------------------------------------------------
# classify_error — CODE_ERROR (default)
# ---------------------------------------------------------------------------


class TestClassifyErrorCodeError:
    def test_syntax_error(self):
        result = classify_error("SyntaxError", "invalid syntax at line 42")
        assert result == ErrorCategory.CODE_ERROR

    def test_type_error(self):
        result = classify_error("TypeError", "unsupported operand type: str + int")
        assert result == ErrorCategory.CODE_ERROR

    def test_logic_error(self):
        result = classify_error("ValueError", "expected list, got dict")
        assert result == ErrorCategory.CODE_ERROR

    def test_attribute_error(self):
        result = classify_error("AttributeError", "object has no attribute 'run'")
        assert result == ErrorCategory.CODE_ERROR

    def test_import_error(self):
        result = classify_error("ImportError", "cannot import name 'foo' from 'bar'")
        assert result == ErrorCategory.CODE_ERROR

    def test_unknown_error_defaults_to_code_error(self):
        result = classify_error("UnknownExceptionType", "something went wrong")
        assert result == ErrorCategory.CODE_ERROR

    def test_empty_message_defaults_to_code_error(self):
        result = classify_error("RuntimeError", "")
        assert result == ErrorCategory.CODE_ERROR

    def test_empty_type_defaults_to_code_error(self):
        result = classify_error("", "some message")
        assert result == ErrorCategory.CODE_ERROR


# ---------------------------------------------------------------------------
# build_error_signature — deterministic and stable
# ---------------------------------------------------------------------------


class TestBuildErrorSignature:
    def test_format_is_project_type_hash(self):
        sig = build_error_signature("proj-123", "SyntaxError", "invalid syntax")
        parts = sig.split(":")
        assert len(parts) == 3
        assert parts[0] == "proj-123"
        assert parts[1] == "SyntaxError"
        assert len(parts[2]) == 8  # 8-char MD5 prefix

    def test_deterministic_same_inputs(self):
        sig1 = build_error_signature("proj-abc", "TypeError", "cannot add str+int")
        sig2 = build_error_signature("proj-abc", "TypeError", "cannot add str+int")
        assert sig1 == sig2

    def test_different_messages_produce_different_hashes(self):
        sig1 = build_error_signature("proj-abc", "TypeError", "cannot add str+int")
        sig2 = build_error_signature("proj-abc", "TypeError", "cannot multiply str*int")
        assert sig1 != sig2

    def test_different_error_types_produce_different_sigs(self):
        sig1 = build_error_signature("proj-abc", "SyntaxError", "bad code")
        sig2 = build_error_signature("proj-abc", "TypeError", "bad code")
        assert sig1 != sig2

    def test_different_projects_produce_different_sigs(self):
        sig1 = build_error_signature("proj-1", "SyntaxError", "bad code")
        sig2 = build_error_signature("proj-2", "SyntaxError", "bad code")
        assert sig1 != sig2

    def test_hash_is_md5_first_8_chars(self):
        message = "invalid syntax"
        expected_hash = hashlib.md5(message.encode(), usedforsecurity=False).hexdigest()[:8]
        sig = build_error_signature("proj-x", "SyntaxError", message)
        assert sig.endswith(f":{expected_hash}")

    def test_empty_project_id(self):
        sig = build_error_signature("", "SyntaxError", "bad code")
        assert sig.startswith(":")

    def test_signature_is_stable_string(self):
        sig = build_error_signature("proj-123", "TypeError", "error msg")
        assert isinstance(sig, str)
        assert len(sig) > 0
