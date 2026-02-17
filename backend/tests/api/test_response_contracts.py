"""Response contract validation tests.

Validates CNTR-01 (stable shapes) and CNTR-02 (empty arrays not null) requirements.
Tests that all list-typed fields in response models default to [] instead of null.

CNTR-01: All response models have stable, predictable shapes.
CNTR-02: List fields serialize as [] not null when no data exists.
"""

import pytest

from app.schemas.dashboard import DashboardResponse
from app.schemas.decision_gates import CreateGateResponse, GateStatusResponse, GATE_1_OPTIONS
from app.schemas.timeline import TimelineResponse
from app.schemas.strategy_graph import GraphResponse


# ---------------------------------------------------------------------------
# Dashboard contract tests
# ---------------------------------------------------------------------------


def test_dashboard_response_empty_arrays_not_null():
    """CNTR-02: Dashboard empty states return [] not null."""
    response = DashboardResponse(
        project_id="test",
        stage=0,
        stage_name="Pre-stage",
        product_version="v0.1",
        mvp_completion_percent=0,
        suggested_focus="All clear",
    )
    assert isinstance(response.artifacts, list) and response.artifacts == []
    assert isinstance(response.pending_decisions, list) and response.pending_decisions == []
    assert isinstance(response.risk_flags, list) and response.risk_flags == []
    # Optional scalar fields are OK as None (not lists)
    assert response.latest_build_status is None
    assert response.preview_url is None
    assert response.next_milestone is None


def test_dashboard_response_serialization_no_nulls():
    """CNTR-02: JSON serialization produces [] not null for list fields."""
    response = DashboardResponse(
        project_id="test",
        stage=0,
        stage_name="Pre-stage",
        product_version="v0.1",
        mvp_completion_percent=0,
        suggested_focus="All clear",
    )
    data = response.model_dump()
    assert data["artifacts"] == []
    assert data["pending_decisions"] == []
    assert data["risk_flags"] == []


def test_dashboard_response_list_fields_have_default_factory():
    """CNTR-01: Meta-test — all list fields in DashboardResponse have default_factory."""
    from typing import get_args, get_origin

    for name, field in DashboardResponse.model_fields.items():
        annotation = field.annotation
        origin = get_origin(annotation)
        if origin is list:
            # The field must have a default or default_factory (not a required list)
            has_default = field.default is not None or field.default_factory is not None
            assert has_default, (
                f"DashboardResponse.{name} is list type but has no default — "
                f"will raise ValidationError or serialize as null"
            )


# ---------------------------------------------------------------------------
# Gate response contract tests
# ---------------------------------------------------------------------------


def test_gate_status_response_options_default():
    """CNTR-01: GateStatusResponse options field has stable shape ([] not null)."""
    response = GateStatusResponse(
        gate_id="gate-001",
        gate_type="direction",
        status="pending",
    )
    # options must default to [] not None
    assert isinstance(response.options, list) and response.options == []


def test_gate_status_response_serialization():
    """CNTR-02: GateStatusResponse serializes options as [] not null."""
    response = GateStatusResponse(
        gate_id="gate-001",
        gate_type="direction",
        status="pending",
    )
    data = response.model_dump()
    assert data["options"] == []
    # Scalar nullable fields are OK as None
    assert data["decision"] is None
    assert data["decided_at"] is None


def test_create_gate_response_shape():
    """CNTR-01: CreateGateResponse has stable shape with non-empty options list."""
    response = CreateGateResponse(
        gate_id="gate-002",
        gate_type="direction",
        status="pending",
        options=GATE_1_OPTIONS,
        created_at="2026-01-01T00:00:00Z",
    )
    assert isinstance(response.options, list)
    assert len(response.options) == 4  # Gate 1 has 4 locked options


# ---------------------------------------------------------------------------
# Timeline contract tests
# ---------------------------------------------------------------------------


def test_timeline_response_empty_arrays_not_null():
    """CNTR-02: TimelineResponse empty states return [] not null."""
    response = TimelineResponse(project_id="proj-001")
    assert isinstance(response.items, list) and response.items == []
    assert response.total == 0


def test_timeline_response_serialization():
    """CNTR-02: TimelineResponse serializes items as [] not null."""
    response = TimelineResponse(project_id="proj-001")
    data = response.model_dump()
    assert data["items"] == []
    assert data["total"] == 0


# ---------------------------------------------------------------------------
# Graph response contract tests
# ---------------------------------------------------------------------------


def test_graph_response_empty_arrays_not_null():
    """CNTR-02: GraphResponse empty states return [] not null for nodes and edges."""
    response = GraphResponse(project_id="proj-001")
    assert isinstance(response.nodes, list) and response.nodes == []
    assert isinstance(response.edges, list) and response.edges == []


def test_graph_response_serialization():
    """CNTR-02: GraphResponse serializes nodes and edges as [] not null."""
    response = GraphResponse(project_id="proj-001")
    data = response.model_dump()
    assert data["nodes"] == []
    assert data["edges"] == []


# ---------------------------------------------------------------------------
# Meta-test: scan all response models
# ---------------------------------------------------------------------------


def test_all_dashboard_response_list_fields_have_defaults():
    """CNTR-02: Meta-test — scan DashboardResponse model for list fields missing defaults."""
    from typing import get_origin

    for name, field in DashboardResponse.model_fields.items():
        annotation = field.annotation
        origin = get_origin(annotation)
        if origin is list:
            assert field.default is not None or field.default_factory is not None, (
                f"Field '{name}' is list type but has no default — will serialize as null"
            )


def test_timeline_response_list_field_has_default():
    """CNTR-02: TimelineResponse.items has default_factory=list."""
    from typing import get_origin

    items_field = TimelineResponse.model_fields["items"]
    origin = get_origin(items_field.annotation)
    assert origin is list, "items should be list-typed"
    assert items_field.default_factory is not None, (
        "TimelineResponse.items has no default_factory — may serialize as null"
    )


def test_graph_response_list_fields_have_defaults():
    """CNTR-02: GraphResponse.nodes and GraphResponse.edges have default_factory=list."""
    from typing import get_origin

    for name in ("nodes", "edges"):
        field = GraphResponse.model_fields[name]
        origin = get_origin(field.annotation)
        assert origin is list, f"{name} should be list-typed"
        assert field.default_factory is not None, (
            f"GraphResponse.{name} has no default_factory — may serialize as null"
        )


def test_gate_status_response_options_has_default():
    """CNTR-02: GateStatusResponse.options has default_factory=list (not None)."""
    from typing import get_origin

    options_field = GateStatusResponse.model_fields["options"]
    origin = get_origin(options_field.annotation)
    assert origin is list, "options should be list-typed"
    assert options_field.default_factory is not None, (
        "GateStatusResponse.options has no default_factory — will serialize as null"
    )
