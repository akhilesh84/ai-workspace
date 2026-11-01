"""Tests for Nifty Energy Quality Basket MCP Server tools."""

import sys
from pathlib import Path

src_dir = Path(__file__).resolve().parent.parent / "src" / "server"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from tools.energy_basket import (
    BASKET_CONFIG,
    get_fallback,
    evaluate_signal,
    evaluate_energy_basket,
)


def test_basket_config_stocks():
    expected_tickers = {"COALINDIA", "POWERGRID", "PETRONET", "BPCL", "CASTROLIND"}
    assert set(BASKET_CONFIG.keys()) == expected_tickers
    total_target_weight = sum(cfg["target_weight"] for cfg in BASKET_CONFIG.values())
    assert abs(total_target_weight - 1.0) < 1e-6


def test_get_fallback():
    for ticker in BASKET_CONFIG:
        fallback = get_fallback(ticker)
        assert "price" in fallback and fallback["price"] > 0
        assert "pe" in fallback and fallback["pe"] > 0
        assert "pb" in fallback and fallback["pb"] > 0
        assert "div_yield" in fallback and fallback["div_yield"] > 0


def test_evaluate_signal_pause():
    # Test pause condition for Coal India (pe_min: 9.8, pb_min: 2.75)
    data = {"price": 500.0, "pe": 10.5, "pb": 3.0, "div_yield": 4.0}
    signal, mult, notes = evaluate_signal("COALINDIA", data)
    assert signal == "PAUSE / TRIM"
    assert mult == 0.0


def test_evaluate_signal_tier3():
    # Test tier 3 condition for Coal India (yield >= 7.8)
    data = {"price": 400.0, "pe": 6.0, "pb": 1.6, "div_yield": 8.0}
    signal, mult, notes = evaluate_signal("COALINDIA", data)
    assert signal == "TIER 3 (LUMP SUM)"
    assert mult == 3.0


def test_evaluate_energy_basket_execution():
    result = evaluate_energy_basket(monthly_budget=50000.0)
    assert result["status"] == "success"
    assert result["monthly_budget_inr"] == 50000.0
    assert "allocations" in result
    assert len(result["allocations"]) > 0

    allocated_sum = sum(
        alloc["monthly_tranche_inr"] for alloc in result["allocations"].values()
    )
    # Total allocated plus redirected pool should approximately equal monthly budget
    assert abs(allocated_sum + result["paused_pool_redirected_inr"] - 50000.0) < 5.0


if __name__ == "__main__":
    test_basket_config_stocks()
    print("✓ test_basket_config_stocks passed")
    test_get_fallback()
    print("✓ test_get_fallback passed")
    test_evaluate_signal_pause()
    print("✓ test_evaluate_signal_pause passed")
    test_evaluate_signal_tier3()
    print("✓ test_evaluate_signal_tier3 passed")
    test_evaluate_energy_basket_execution()
    print("✓ test_evaluate_energy_basket_execution passed")
    print("All tests passed successfully!")

