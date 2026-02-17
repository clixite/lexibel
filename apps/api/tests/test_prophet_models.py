"""Tests for PROPHET models."""
import uuid

import pytest

from packages.db.models.prophet_prediction import ProphetPrediction
from packages.db.models.prophet_simulation import ProphetSimulation


def test_prophet_prediction_model():
    """Test ProphetPrediction model structure."""
    case_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000002")

    prediction = ProphetPrediction(
        tenant_id=tenant_id,
        case_id=case_id,
        prediction_type="outcome",
        predicted_value=0.75,
        confidence_interval_low=0.65,
        confidence_interval_high=0.85,
        confidence_score=0.90,
        model_version="v1.0",
        features_used={"age": 30},
        shap_values={"feature1": 0.5},
        risk_factors=[{"factor": "delay", "weight": 0.3}],
        positive_factors=[{"factor": "precedent", "weight": 0.6}],
    )

    assert prediction.prediction_type == "outcome"
    assert prediction.predicted_value == 0.75
    assert prediction.confidence_interval_low == 0.65
    assert prediction.confidence_interval_high == 0.85
    assert prediction.confidence_score == 0.90
    assert prediction.model_version == "v1.0"
    assert prediction.features_used == {"age": 30}
    assert prediction.shap_values == {"feature1": 0.5}
    assert prediction.risk_factors == [{"factor": "delay", "weight": 0.3}]
    assert prediction.positive_factors == [{"factor": "precedent", "weight": 0.6}]
    assert prediction.case_id == case_id
    assert prediction.tenant_id == tenant_id


def test_prophet_simulation_model():
    """Test ProphetSimulation model structure."""
    case_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000002")

    simulation = ProphetSimulation(
        tenant_id=tenant_id,
        case_id=case_id,
        strategy_name="négociation",
        success_probability=0.80,
        estimated_amount_median=50000.0,
        estimated_amount_range_low=40000.0,
        estimated_amount_range_high=60000.0,
        estimated_duration_months=6.0,
        estimated_costs=5000.0,
        recommendation_score=0.85,
    )

    assert simulation.strategy_name == "négociation"
    assert simulation.success_probability == 0.80
    assert simulation.estimated_amount_median == 50000.0
    assert simulation.estimated_amount_range_low == 40000.0
    assert simulation.estimated_amount_range_high == 60000.0
    assert simulation.estimated_duration_months == 6.0
    assert simulation.estimated_costs == 5000.0
    assert simulation.recommendation_score == 0.85
    assert simulation.case_id == case_id
    assert simulation.tenant_id == tenant_id
