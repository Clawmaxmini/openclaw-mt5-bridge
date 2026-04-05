"""Market state engine with pulse detection and regime classification."""
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from .config import settings
from .file_store import file_store
from .state_models import (
    Direction,
    MarketRegime,
    MarketState,
    MarketStateSummary,
    ResonanceCheck,
    ResonanceLevel,
    StateType,
    StrategyPermission,
)

logger = logging.getLogger(__name__)

# === Configuration ===
STATE_WINDOW_SECONDS = 180  # 3 minutes
STATE_REEVAL_SECONDS = 30

# Minimum hold times (seconds)
MIN_HOLD_CANDIDATE = 90
MIN_HOLD_CONFIRMED = 300
MIN_HOLD_FALSE = 120
MIN_HOLD_RANGE = 300
MIN_HOLD_QUIET = 300

# Validation symbol mappings
VALIDATION_MAPPING = {
    "JP225": ["USDJPY", "US500", "XAUUSD", "BTCUSD"],
    "XAUUSD": ["XAGUSD", "USDJPY", "US500", "EURUSD"],
    "USDJPY": ["JP225", "US500", "XAUUSD", "EURUSD"],
    "BTCUSD": ["US500", "XAUUSD", "USDJPY"],
}

# Regime inference rules
REGIME_RULES = {
    "JP225": {
        "up_logic": {"USDJPY": "up", "US500": "up_or_not_weak", "XAUUSD": "down_or_not_strong"},
        "down_logic": {"USDJPY": "down", "US500": "down_or_weak", "XAUUSD": "up"},
    },
    "XAUUSD": {
        "up_logic": {"XAGUSD": "up", "USDJPY": "down", "US500": "down"},
        "down_logic": {"XAGUSD": "down", "USDJPY": "up_or_not_strong", "US500": "up_or_not_weak"},
    },
}


def _load_snapshots(symbol: str, seconds: int = STATE_WINDOW_SECONDS) -> list[dict]:
    """Load recent snapshots for a symbol."""
    try:
        path = file_store.resolve_path(settings.snapshot_dir, f"{symbol.upper()}.jsonl")
        if not file_store.exists(path):
            return []
        
        rows = file_store.read_jsonl(path)
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=seconds)
        
        filtered = []
        for row in rows:
            ts_str = row.get("timestamp_utc") or row.get("time")
            if ts_str:
                try:
                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    if ts >= cutoff:
                        filtered.append(row)
                except (ValueError, TypeError):
                    continue
        
        return filtered[-30:]  # Limit to last 30 snapshots
    except Exception as exc:
        logger.warning("Failed to load snapshots for %s: %s", symbol, exc)
        return []


def _compute_anomaly_score(snapshots: list[dict]) -> int:
    """Compute anomaly score (0-100) based on price displacement and volatility."""
    if len(snapshots) < 3:
        return 0
    
    try:
        prices = [(s.get("bid", 0) + s.get("ask", 0)) / 2 for s in snapshots]
        if len(prices) < 2:
            return 0
        
        # Calculate returns
        returns = [(prices[i] - prices[i-1]) / prices[i-1] * 100 for i in range(1, len(prices))]
        if not returns:
            return 0
        
        # Simple volatility measure
        avg_return = sum(abs(r) for r in returns[-6:]) / min(6, len(returns))
        
        # Displacement in last window
        displacement = abs(prices[-1] - prices[0]) / prices[0] * 100 if prices[0] else 0
        
        # Combine into anomaly score (0-100)
        score = min(100, int((avg_return * 10 + displacement * 5)))
        return min(100, max(0, score))
    except Exception as exc:
        logger.warning("Failed to compute anomaly score: %s", exc)
        return 0


def _compute_quality_score(snapshots: list[dict]) -> int:
    """Compute quality score based on hold time and structure."""
    if len(snapshots) < 2:
        return 50  # Neutral
    
    try:
        # Calculate basic metrics
        prices = [(s.get("bid", 0) + s.get("ask", 0)) / 2 for s in snapshots]
        if len(prices) < 2:
            return 50
        
        # Peak and current
        peak = max(prices)
        current = prices[-1]
        trough = min(prices)
        
        # Retraction ratio (0-1, lower is better)
        total_move = peak - trough
        retraction = (peak - current) / total_move if total_move > 0 else 0
        
        # Hold time estimate (snapshots count as proxy)
        hold_factor = min(1.0, len(snapshots) / 10)
        
        # Secondary push detection (check if new high after dip)
        secondary = 0
        for i in range(2, len(prices)):
            if prices[i] > prices[i-1] and prices[i-1] < prices[i-2]:
                secondary = 1
                break
        
        # Score composition
        retraction_score = int((1 - min(1, retraction)) * 40)
        hold_score = int(hold_factor * 30)
        secondary_score = secondary * 30
        
        return min(100, max(0, retraction_score + hold_score + secondary_score))
    except Exception as exc:
        logger.warning("Failed to compute quality score: %s", exc)
        return 50


def _compute_resonance_score(symbol: str, direction: Direction, snapshots: list[dict]) -> tuple[int, ResonanceLevel, dict[str, ResonanceCheck]]:
    """Compute resonance score with cross-asset validation."""
    validation_symbols = VALIDATION_MAPPING.get(symbol, [])
    if not validation_symbols:
        return 50, ResonanceLevel.WEAK, {}
    
    checks = {}
    total_score = 0
    matched_count = 0
    
    expected_direction = "up" if direction == Direction.UP else "down" if direction == Direction.DOWN else None
    
    if expected_direction is None:
        return 50, ResonanceLevel.WEAK, {}
    
    regime_rules = REGIME_RULES.get(symbol, {}).get("up_logic" if direction == Direction.UP else "down_logic", {})
    
    for val_symbol in validation_symbols:
        try:
            val_snapshots = _load_snapshots(val_symbol, seconds=60)
            if not val_snapshots:
                checks[val_symbol] = ResonanceCheck(
                    expected=expected_direction,
                    observed="no_data",
                    matched=False,
                    score=0
                )
                continue
            
            # Compare price direction
            val_prices = [(s.get("bid", 0) + s.get("ask", 0)) / 2 for s in val_snapshots]
            if len(val_prices) >= 2:
                val_change = (val_prices[-1] - val_prices[0]) / val_prices[0] * 100
                val_direction = "up" if val_change > 0.01 else "down" if val_change < -0.01 else "flat"
            else:
                val_direction = "flat"
            
            expected = regime_rules.get(val_symbol, expected_direction)
            
            matched = (
                (expected == "up" and val_direction == "up") or
                (expected == "down" and val_direction == "down") or
                (expected in ("up_or_not_weak", "up_or_not_strong") and val_direction in ("up", "flat")) or
                (expected in ("down_or_weak", "down_or_not_strong") and val_direction in ("down", "flat"))
            )
            
            score = 2 if matched else 0
            total_score += score
            matched_count += 1
            
            checks[val_symbol] = ResonanceCheck(
                expected=expected,
                observed=val_direction,
                matched=matched,
                score=score
            )
        except Exception as exc:
            logger.warning("Resonance check failed for %s: %s", val_symbol, exc)
            checks[val_symbol] = ResonanceCheck(
                expected=expected_direction,
                observed="error",
                matched=False,
                score=0
            )
    
    if matched_count == 0:
        return 50, ResonanceLevel.WEAK, checks
    
    # Normalize score (max 4 validation symbols * 2 points = 8)
    normalized = int((total_score / (matched_count * 2)) * 100)
    
    if normalized >= 60:
        level = ResonanceLevel.STRONG
    elif normalized >= 30:
        level = ResonanceLevel.WEAK
    else:
        level = ResonanceLevel.NONE
    
    return normalized, level, checks


def _infer_macro_regime(symbol: str, direction: Direction, resonance: ResonanceLevel) -> MarketRegime:
    """Infer macro regime based on symbol and resonance."""
    if resonance == ResonanceLevel.NONE:
        return MarketRegime.UNKNOWN
    
    if symbol in ("XAUUSD", "XAGUSD"):
        return MarketRegime.RISK_OFF if direction == Direction.UP else MarketRegime.RISK_ON
    elif symbol in ("JP225", "US500"):
        return MarketRegime.RISK_ON if direction == Direction.UP else MarketRegime.RISK_OFF
    elif symbol == "USDJPY":
        return MarketRegime.USD_DRIVEN
    elif symbol == "BTCUSD":
        return MarketRegime.RISK_ON if direction == Direction.UP else MarketRegime.UNKNOWN
    
    return MarketRegime.MIXED


def _get_strategy_permission(state: StateType, quality: int) -> StrategyPermission:
    """Get strategy permissions based on market state and quality."""
    base_permissions = {
        StateType.QUIET: StrategyPermission(trend="blocked", range_mode="reduced", event="blocked"),
        StateType.RANGE: StrategyPermission(trend="blocked", range_mode="enabled", event="blocked"),
        StateType.CANDIDATE_IMPULSE: StrategyPermission(trend="reduced", range_mode="blocked", event="reduced"),
        StateType.CONFIRMED_IMPULSE: StrategyPermission(trend="enabled", range_mode="blocked", event="enabled"),
        StateType.FALSE_IMPULSE: StrategyPermission(trend="blocked", range_mode="enabled", event="blocked"),
    }
    
    perm = base_permissions.get(state, base_permissions[StateType.QUIET])
    
    # Reduce permissions if quality is low
    if quality < 40:
        if perm.trend == "enabled":
            perm.trend = "reduced"
        if perm.event == "enabled":
            perm.event = "reduced"
    
    return perm


def _generate_chinese_summary(state: MarketState) -> str:
    """Generate human-readable Chinese summary."""
    symbol = state.symbol
    age = state.state_age_seconds
    
    if state.current_state == StateType.QUIET:
        return f"最近{age}秒{symbol}维持平静，暂无明显异常推动。"

    elif state.current_state == StateType.RANGE:
        return f"最近{age}秒{symbol}维持震荡格局，暂无明显趋势方向。"

    elif state.current_state == StateType.CANDIDATE_IMPULSE:
        direction_text = "上行" if state.impulse_direction == Direction.UP else "下行"
        quality_text = "较高" if state.quality_score >= 60 else "中等" if state.quality_score >= 40 else "偏低"
        resonance_text = "强" if state.resonance_level == ResonanceLevel.STRONG else "弱"
        return f"最近{age}秒出现{direction_text}脉冲，异常度{state.anomaly_score}/100，结构质量{quality_text}，共振{resonance_text}，暂列候选脉冲。"

    elif state.current_state == StateType.CONFIRMED_IMPULSE:
        direction_text = "上涨" if state.impulse_direction == Direction.UP else "下跌"
        return f"确认{direction_text}脉冲，异常度{state.anomaly_score}/100，结构质量{state.quality_score}/100，共振{state.resonance_score}/100，趋势策略已启用。"

    elif state.current_state == StateType.FALSE_IMPULSE:
        direction_text = "上行" if state.impulse_direction == Direction.UP else "下行"
        return f"前期{direction_text}已大幅回吐并重回原区间，判定为假脉冲，暂不支持趋势策略。"
    
    return f"{symbol}当前状态：{state.current_state.value}，{age}秒。"


def compute_market_state(symbol: str, previous_state: Optional[MarketState] = None) -> MarketState:
    """Compute current market state for a symbol."""
    snapshots = _load_snapshots(symbol)
    
    # Default state
    state = MarketState(
        symbol=symbol,
        current_state=StateType.QUIET,
        previous_state=previous_state.current_state if previous_state else StateType.QUIET,
        state_enter_time=previous_state.state_enter_time if previous_state else datetime.utcnow().isoformat(),
        updated_at=datetime.utcnow().isoformat(),
    )
    
    if len(snapshots) < 3:
        state.human_readable_summary_cn = f"{symbol}数据不足，暂无状态判断。"
        return state
    
    # Compute scores
    state.anomaly_score = _compute_anomaly_score(snapshots)
    state.quality_score = _compute_quality_score(snapshots)
    
    # Determine direction from recent snapshots
    try:
        prices = [(s.get("bid", 0) + s.get("ask", 0)) / 2 for s in snapshots]
        if len(prices) >= 2:
            change = (prices[-1] - prices[0]) / prices[0] * 100
            if change > 0.05:
                state.impulse_direction = Direction.UP
            elif change < -0.05:
                state.impulse_direction = Direction.DOWN
            else:
                state.impulse_direction = Direction.NONE
    except Exception:
        state.impulse_direction = Direction.NONE
    
    # Resonance
    state.resonance_score, state.resonance_level, state.resonance_checks = _compute_resonance_score(
        symbol, state.impulse_direction, snapshots
    )
    
    # Macro regime
    state.macro_regime_hint = _infer_macro_regime(symbol, state.impulse_direction, state.resonance_level)
    
    # Determine state based on scores
    if state.anomaly_score < 30:
        new_state = StateType.QUIET
        state.transition_reason = "异常度低于阈值"
    elif state.anomaly_score >= 70 and state.quality_score >= 60 and state.resonance_score >= 50:
        new_state = StateType.CONFIRMED_IMPULSE
        state.transition_reason = "异常度高且质量好且共振强"
    elif state.anomaly_score >= 50 and state.quality_score < 40 and state.resonance_score < 40:
        new_state = StateType.FALSE_IMPULSE
        state.transition_reason = "异常度高但质量差且共振弱"
    elif state.anomaly_score >= 40:
        new_state = StateType.CANDIDATE_IMPULSE
        state.transition_reason = "异常度中等，待进一步确认"
    else:
        new_state = StateType.RANGE
        state.transition_reason = "市场处于震荡区间"
    
    # Hysteresis: check minimum hold time before state change
    if previous_state and previous_state.current_state != new_state:
        min_hold = {
            StateType.CANDIDATE_IMPULSE: MIN_HOLD_CANDIDATE,
            StateType.CONFIRMED_IMPULSE: MIN_HOLD_CONFIRMED,
            StateType.FALSE_IMPULSE: MIN_HOLD_FALSE,
            StateType.RANGE: MIN_HOLD_RANGE,
            StateType.QUIET: MIN_HOLD_QUIET,
        }.get(previous_state.current_state, 60)
        
        if previous_state.state_age_seconds < min_hold:
            new_state = previous_state.current_state
            state.transition_reason = f"最短驻留时间未满足（{previous_state.state_age_seconds}<{min_hold}秒），保持原状态"
    
    state.previous_state = previous_state.current_state if previous_state else state.current_state
    state.current_state = new_state
    
    # Update state timing
    if state.current_state != state.previous_state:
        state.state_enter_time = datetime.utcnow().isoformat()
        state.state_age_seconds = 0
    elif previous_state:
        try:
            enter_time = datetime.fromisoformat(state.state_enter_time.replace("Z", "+00:00"))
            state.state_age_seconds = previous_state.state_age_seconds + STATE_REEVAL_SECONDS
        except Exception:
            state.state_age_seconds = previous_state.state_age_seconds + STATE_REEVAL_SECONDS
    else:
        state.state_age_seconds = STATE_REEVAL_SECONDS
    
    # Strategy permissions
    state.strategy_permission = _get_strategy_permission(state.current_state, state.quality_score)
    
    # Human readable summary
    state.human_readable_summary_cn = _generate_chinese_summary(state)
    
    # Possible next states
    state.possible_next_states = {
        StateType.QUIET: ["range", "candidate_impulse"],
        StateType.RANGE: ["quiet", "candidate_impulse"],
        StateType.CANDIDATE_IMPULSE: ["confirmed_impulse", "false_impulse", "range"],
        StateType.CONFIRMED_IMPULSE: ["false_impulse", "range", "quiet"],
        StateType.FALSE_IMPULSE: ["quiet", "range", "candidate_impulse"],
    }.get(state.current_state, [])
    
    return state


class MarketStateEngine:
    """Main market state engine managing multiple symbols."""
    
    def __init__(self) -> None:
        self._states: dict[str, MarketState] = {}
        self._state_dir = Path(settings.data_root) / "state"
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._latest_state_file = self._state_dir / "latest_state.json"
    
    def get_state(self, symbol: str) -> MarketState:
        """Get or compute state for a symbol."""
        previous = self._states.get(symbol)
        state = compute_market_state(symbol, previous)
        self._states[symbol] = state
        self._save_state()
        return state
    
    def get_all_states(self) -> MarketStateSummary:
        """Get states for all known symbols."""
        # Load known symbols from snapshots
        try:
            snapshot_dir = Path(settings.snapshot_dir)
            if snapshot_dir.exists():
                symbols = [p.stem.upper() for p in snapshot_dir.glob("*.jsonl")]
            else:
                symbols = list(self._states.keys())
        except Exception:
            symbols = list(self._states.keys())
        
        for symbol in symbols:
            if symbol not in self._states:
                self.get_state(symbol)
        
        return MarketStateSummary(
            symbols=sorted(self._states.keys()),
            states=self._states.copy(),
            updated_at=datetime.utcnow().isoformat()
        )
    
    def _save_state(self) -> None:
        """Persist state to disk."""
        try:
            data = {
                symbol: state.model_dump()
                for symbol, state in self._states.items()
            }
            with open(self._latest_state_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            logger.warning("Failed to save state: %s", exc)
    
    def load_state(self) -> None:
        """Load state from disk."""
        try:
            if self._latest_state_file.exists():
                with open(self._latest_state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for symbol, state_data in data.items():
                    state_data.pop("strategy_permission", None)
                    self._states[symbol] = MarketState(**state_data)
                logger.info("Loaded state for %d symbols", len(self._states))
        except Exception as exc:
            logger.warning("Failed to load state: %s", exc)


# Global instance
market_state_engine = MarketStateEngine()
market_state_engine.load_state()
