"""Regression tests for waveform validity and audit integrity."""
import csv
import math

import pytest

from agents.base import AuditTrail, SecurityException
from agents.models import SystemTaskPayload
from agents.supervisor import SystemSupervisor
from spirometry_analyzer.curve_metrics import Waveform, compute_metrics, load_waveform_csv
from spirometry_analyzer import gli2012
from spiro_analyze import interpret_spirometry, bronchodilator_response

import numpy as np


def test_audit_signature_recomputed():
    trail = AuditTrail(secret_key="unit-test-only")
    trail.log("test", "dev", "event", {"status": "OK"})
    assert trail.verify_integrity()
    trail.logs[0]["actor"] = "attacker"
    assert not trail.verify_integrity()


def test_audit_trail_copy_cannot_mutate_original():
    trail = AuditTrail(secret_key="unit-test-only")
    trail.log("test", "dev", "event", {"status": "OK"})
    trail.get_trail()[0]["actor"] = "tampering"
    assert trail.verify_integrity()


def test_nested_identifiers_blocked():
    supervisor = SystemSupervisor(model_provider="mock")
    with pytest.raises(SecurityException):
        supervisor.process_task(SystemTaskPayload(
            task_id="CASE-001", target_identifier="KEY-123", primary_metric=1,
            attributes={"nested": {"mrn": "MRN-123456"}},
        ))


def test_invalid_waveforms_rejected(tmp_path):
    invalid = tmp_path / "invalid.csv"
    invalid.write_text("time_s,flow_Lps\n0,1\n0,1\n2,1\n", encoding="utf8")
    with pytest.raises(ValueError, match="unique"):
        load_waveform_csv(str(invalid))
    invalid.write_text("time_s,flow_Lps\n0,1\n1,nan\n2,1\n", encoding="utf8")
    with pytest.raises(ValueError, match="finite"):
        load_waveform_csv(str(invalid))
    invalid.write_text("time_s,flow_Lps\n0,1\n.5,1\n", encoding="utf8")
    with pytest.raises(ValueError, match="three"):
        load_waveform_csv(str(invalid))


def test_short_recordings_rejected():
    t = np.array([0., 0.2, 0.4])
    with pytest.raises(ValueError, match="one second"):
        compute_metrics(Waveform(t, np.array([0., .2, .4]), np.array([1., 1., 1.])))


def test_glide_approximation_adults_only():
    with pytest.raises(ValueError, match="18-95"):
        gli2012.predicted(10, 140, "M", "caucasian", "FEV1")


def test_legacy_inputs_and_response_validated():
    with pytest.raises(ValueError, match="exceed"):
        interpret_spirometry(3.1, 3.0, 50, 170, "M")
    with pytest.raises(ValueError, match="finite"):
        interpret_spirometry(float("nan"), 3.0, 50, 170, "M")
    with pytest.raises(ValueError, match="finite"):
        bronchodilator_response(2, float("nan"))
