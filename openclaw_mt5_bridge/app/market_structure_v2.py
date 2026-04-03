from typing import Any


def _max_pullback_pct(closes: list[float], first_open: float) -> float:
    if not closes or first_open == 0:
        return 0.0

    peak = closes[0]
    max_pullback = 0.0
    for price in closes:
        if price > peak:
            peak = price
        pullback = (peak - price) / first_open
        if pullback > max_pullback:
            max_pullback = pullback
    return max_pullback


def detect_market_structure_v2(symbol: str, bars: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    if not bars:
        return {
            "symbol": symbol,
            "structure": "range",
            "metrics": {
                "up_ratio": 0.0,
                "net_change_pct": 0.0,
                "efficiency_ratio": 0.0,
                "max_pullback_pct": 0.0,
                "midpoint_index": 0,
            },
        }

    total = len(bars)
    up_count = sum(1 for c in bars if c["close"] > c["open"])
    up_ratio = up_count / total

    first_open = float(bars[0]["open"])
    last_close = float(bars[-1]["close"])
    net_change_pct = 0.0 if first_open == 0 else (last_close - first_open) / first_open

    path_sum = 0.0
    for i in range(1, total):
        path_sum += abs(float(bars[i]["close"]) - float(bars[i - 1]["close"]))
    efficiency_ratio = 0.0 if path_sum == 0 else abs(last_close - first_open) / path_sum

    lows = [float(c["low"]) for c in bars]
    highs = [float(c["high"]) for c in bars]
    closes = [float(c["close"]) for c in bars]

    low_index = min(range(total), key=lambda i: lows[i])
    high_index = max(range(total), key=lambda i: highs[i])
    lowest_low = lows[low_index]
    highest_high = highs[high_index]

    midpoint_low = low_index / total
    midpoint_high = high_index / total

    trend_threshold = float(config["trend_threshold"])
    net_move_threshold_pct = float(config["net_move_threshold_pct"])
    efficiency_threshold = float(config["efficiency_threshold"])
    v_shape_recovery_ratio = float(config["v_shape_recovery_ratio"])
    v_mid_min = float(config["v_shape_midpoint_min"])
    v_mid_max = float(config["v_shape_midpoint_max"])
    range_eff = float(config["range_efficiency_threshold"])
    range_net = float(config["range_net_move_threshold_pct"])

    structure = "range"
    midpoint_index = min(low_index, high_index)

    if (
        up_ratio >= trend_threshold
        and net_change_pct >= net_move_threshold_pct
        and efficiency_ratio >= efficiency_threshold
    ):
        structure = "trend_up"
        midpoint_index = high_index
    elif (
        up_ratio <= (1 - trend_threshold)
        and net_change_pct <= -net_move_threshold_pct
        and efficiency_ratio >= efficiency_threshold
    ):
        structure = "trend_down"
        midpoint_index = low_index
    elif v_mid_min <= midpoint_low <= v_mid_max and first_open > lowest_low:
        left_drop = (first_open - lowest_low) / first_open if first_open else 0.0
        right_rebound = (last_close - lowest_low) / first_open if first_open else 0.0
        recovery_ratio = (last_close - lowest_low) / (first_open - lowest_low)

        if (
            left_drop >= net_move_threshold_pct
            and right_rebound >= net_move_threshold_pct
            and recovery_ratio >= v_shape_recovery_ratio
        ):
            structure = "v_reversal"
            midpoint_index = low_index
    elif v_mid_min <= midpoint_high <= v_mid_max and highest_high > first_open:
        left_rise = (highest_high - first_open) / first_open if first_open else 0.0
        right_drop = (highest_high - last_close) / first_open if first_open else 0.0
        unwind_ratio = (highest_high - last_close) / (highest_high - first_open)

        if (
            left_rise >= net_move_threshold_pct
            and right_drop >= net_move_threshold_pct
            and unwind_ratio >= v_shape_recovery_ratio
        ):
            structure = "inverted_v"
            midpoint_index = high_index

    if structure == "range" and abs(net_change_pct) < range_net and efficiency_ratio < range_eff:
        structure = "range"

    return {
        "symbol": symbol,
        "structure": structure,
        "metrics": {
            "up_ratio": up_ratio,
            "net_change_pct": net_change_pct,
            "efficiency_ratio": efficiency_ratio,
            "max_pullback_pct": _max_pullback_pct(closes, first_open),
            "midpoint_index": midpoint_index,
        },
    }
