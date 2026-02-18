"""Tests for deploy readiness checks domain function.

Pure TDD tests - written before implementation.
Tests cover: complete workspace, missing README, missing env, secrets, no start script,
deploy paths constant, and overall status computation.
"""
import pytest

from app.domain.deploy_checks import (
    DEPLOY_PATHS,
    compute_overall_status,
    run_deploy_checks,
)

pytestmark = pytest.mark.unit


def test_all_checks_pass_with_complete_workspace():
    files = {
        "README.md": "# My App",
        ".env.example": "API_KEY=your_key_here",
        "package.json": '{"scripts": {"start": "node index.js"}, "dependencies": {"express": "4.18"}}',
        "index.js": "const express = require('express')",
    }
    checks = run_deploy_checks(files)
    passing = [c for c in checks if c.status == "pass"]
    assert len(passing) >= 4


def test_missing_readme_is_warning():
    files = {".env.example": "KEY=val", "package.json": '{"scripts":{"start":"node ."}}'}
    checks = run_deploy_checks(files)
    readme_check = next(c for c in checks if c.id == "readme")
    assert readme_check.status == "warn"


def test_missing_env_example_is_warning():
    files = {"README.md": "hi", "package.json": '{"scripts":{"start":"node ."}}'}
    checks = run_deploy_checks(files)
    env_check = next(c for c in checks if c.id == "env_example")
    assert env_check.status == "warn"


def test_hardcoded_secrets_fail():
    files = {"config.py": 'API_KEY="sk-1234567890abcdef"', "README.md": "hi"}
    checks = run_deploy_checks(files)
    secrets_check = next(c for c in checks if c.id == "no_secrets")
    assert secrets_check.status == "fail"
    assert secrets_check.fix_instruction is not None


def test_no_start_script_fail():
    files = {"README.md": "hi", "main.py": "print('hello')"}
    checks = run_deploy_checks(files)
    start_check = next(c for c in checks if c.id == "start_script")
    assert start_check.status == "fail"


def test_deploy_paths_constant():
    assert len(DEPLOY_PATHS) == 3
    ids = [p.id for p in DEPLOY_PATHS]
    assert "vercel" in ids
    assert "railway" in ids
    assert "aws" in ids


def test_overall_status_from_checks():
    files = {"README.md": "hi", ".env.example": "K=V", "package.json": '{"scripts":{"start":"node ."}}'}
    checks = run_deploy_checks(files)
    overall = compute_overall_status(checks)
    assert overall in ["green", "yellow", "red"]
