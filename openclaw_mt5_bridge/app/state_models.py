"""Market state models for pulse detection and regime classification."""
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class StateType(str, Enum):
    """Market state enumeration."""
    QUIET = "quiet"
    RANGE = "range"
    CANDIDATE_IMPULSE = "candidate_impulse"
    CONFIRMED_IMPULSE = "confirmed_impulse"
    FALSE_IMPULSE = "false_impulse"


class Direction(str, Enum):
    """Impulse direction enumeration."""
    UP = "up"
    DOWN = "down"
    MIXED = "mixed"
    NONE = "none"


class MarketRegime(str, Enum):
    """Macro market regime."""
    RISK_ON = "risk_on"
    RISK_OFF = "risk_off"
    USD_DRIVEN = "usd_driven"
    COMMODITY_DRIVEN = "commodity_driven"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class ResonanceLevel(str, Enum):
    """Resonance strength level."""
    NONE = "none"
    WEAK = "weak"
    STRONG = "strong"


class StrategyPermission(BaseModel):
    """Strategy routing permissions based on market state."""
    trend: str = Field(description="trend strategy: enabled/reduced/blocked")
    range_mode: str = Field(description="range strategy: enabled/reduced/blocked")
    event: str = Field(description="event-driven strategy: enabled/reduced/blocked")


class ResonanceCheck(BaseModel):
    """Individual resonance check result."""
    expected: str
    observed: str
    matched: bool
    score: int


class MarketState(BaseModel):
    """Complete market state for a single symbol."""
    symbol: str
    current_state: StateType = StateType.QUIET
    previous_state: StateType = StateType.QUIET
    impulse_direction: Direction = Direction.NONE
    
    state_enter_time: Optional[str] = None
    state_age_seconds: int = 0
    
    anomaly_score: int = Field(default=0, ge=0, le=100)
    quality_score: int = Field(default=0, ge=0, le=100)
    resonance_score: int = Field(default=0, ge=0, le=100)
    
    resonance_level: ResonanceLevel = ResonanceLevel.NONE
    macro_regime_hint: MarketRegime = MarketRegime.UNKNOWN
    
    strategy_permission: StrategyPermission = Field(
        default_factory=lambda: StrategyPermission(
            trend="blocked", range_mode="reduced", event="blocked"
        )
    )
    
    transition_reason: str = ""
    unmet_conditions: list[str] = Field(default_factory=list)
    possible_next_states: list[str] = Field(default_factory=list)
    
    human_readable_summary_cn: str = ""
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    
    # Internal metrics
    retraction_ratio: float = 0.0
    hold_time_seconds: int = 0
    returned_to_range: bool = False
    secondary_push: bool = False
    cross_asset_resonance: bool = False
    
    # Resonance details
    resonance_checks: dict[str, ResonanceCheck] = Field(default_factory=dict)


class MarketStateSummary(BaseModel):
    """Summary of market states across multiple symbols."""
    symbols: list[str]
    states: dict[str, MarketState]
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
