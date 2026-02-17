"""Tests for alignment score domain function.

Pure TDD tests - written before implementation.
Tests cover: empty changes, fully aligned, mixed, scope creep, no original features, case insensitivity.
"""
import pytest

from app.domain.alignment import compute_alignment_score


def test_no_changes_returns_100():
    score, creep = compute_alignment_score({"core_features": [{"name": "Auth"}, {"name": "Dashboard"}]}, [])
    assert score == 100
    assert creep is False


def test_all_aligned_changes():
    scope = {"core_features": [{"name": "Auth"}, {"name": "Dashboard"}]}
    changes = [{"description": "Fix auth login flow"}, {"description": "Add dashboard filter"}]
    score, creep = compute_alignment_score(scope, changes)
    assert score == 100
    assert creep is False


def test_mixed_aligned_and_new():
    scope = {"core_features": [{"name": "Auth"}, {"name": "Dashboard"}]}
    changes = [
        {"description": "Fix auth login flow"},
        {"description": "Add payments integration"},  # New feature
        {"description": "Add dashboard charts"},
    ]
    score, creep = compute_alignment_score(scope, changes)
    assert score == 66  # 2/3 aligned, int truncation
    assert creep is False  # 66 >= 60


def test_all_new_features_scope_creep():
    scope = {"core_features": [{"name": "Auth"}]}
    changes = [{"description": "Add payments"}, {"description": "Add social media"}]
    score, creep = compute_alignment_score(scope, changes)
    assert score == 0
    assert creep is True  # 0 < 60


def test_no_original_features_returns_neutral():
    score, creep = compute_alignment_score({}, [{"description": "anything"}])
    assert score == 75
    assert creep is False


def test_case_insensitive_matching():
    scope = {"core_features": [{"name": "User Auth"}]}
    changes = [{"description": "update USER AUTH flow"}]
    score, creep = compute_alignment_score(scope, changes)
    assert score == 100
