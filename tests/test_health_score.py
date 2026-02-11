from app import compute_health_score, top_drivers, next_steps
from db import CheckHistory


def make_history():
    return [
        CheckHistory(
            user_id=1,
            net_income=3000,
            fixed_expenses=1800,
            today_expense=90,
            days_left=12,
            daily_budget=100,
            status="ok",
            message="ok",
        ),
        CheckHistory(
            user_id=1,
            net_income=3000,
            fixed_expenses=1800,
            today_expense=140,
            days_left=10,
            daily_budget=100,
            status="caution",
            message="caution",
        ),
        CheckHistory(
            user_id=1,
            net_income=3000,
            fixed_expenses=1800,
            today_expense=180,
            days_left=9,
            daily_budget=100,
            status="danger",
            message="danger",
        ),
    ]


def test_compute_health_score_deterministic():
    history = make_history()
    score, meta = compute_health_score(history)
    assert 0 <= score <= 100
    assert "breakdown" in meta
    assert "risk" in meta


def test_top_drivers_and_next_steps():
    history = make_history()
    score, meta = compute_health_score(history)
    drivers = top_drivers(meta["breakdown"])
    steps = next_steps(meta["breakdown"])
    assert len(drivers) == 3
    assert len(steps) >= 1
