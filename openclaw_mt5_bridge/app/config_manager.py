import json
import logging
from copy import deepcopy
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
ACTIVE_SYMBOLS_PATH = BASE_DIR / "symbols_config.json"
ACTIVE_RISK_PATH = BASE_DIR / "risk_config.json"
ACTIVE_MARKET_STRUCTURE_PATH = BASE_DIR / "config" / "market_structure_config.json"
DRAFT_SYMBOLS_PATH = BASE_DIR / "symbols_config.draft.json"
DRAFT_RISK_PATH = BASE_DIR / "risk_config.draft.json"
DRAFT_MARKET_STRUCTURE_PATH = BASE_DIR / "config" / "market_structure_config.draft.json"


class ConfigManager:
    def __init__(self) -> None:
        self.active_config = {"symbols": {}, "risk": {}, "market_structure": {}}
        self.draft_config = {"symbols": {}, "risk": {}, "market_structure": {}}
        self.reload()

    def _read_json(self, path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def _write_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2)

    def reload(self) -> None:
        symbols = self._read_json(ACTIVE_SYMBOLS_PATH)
        risk = self._read_json(ACTIVE_RISK_PATH)
        market_structure = self._read_json(ACTIVE_MARKET_STRUCTURE_PATH)
        self.active_config = {
            "symbols": symbols,
            "risk": risk,
            "market_structure": market_structure,
        }

        if DRAFT_SYMBOLS_PATH.exists() and DRAFT_RISK_PATH.exists() and DRAFT_MARKET_STRUCTURE_PATH.exists():
            self.draft_config = {
                "symbols": self._read_json(DRAFT_SYMBOLS_PATH),
                "risk": self._read_json(DRAFT_RISK_PATH),
                "market_structure": self._read_json(DRAFT_MARKET_STRUCTURE_PATH),
            }
        else:
            self.reset_draft()

    def get_active(self) -> dict[str, Any]:
        return deepcopy(self.active_config)

    def get_draft(self) -> dict[str, Any]:
        return deepcopy(self.draft_config)

    def update_draft(self, payload: dict[str, Any]) -> dict[str, Any]:
        if "symbols" in payload and isinstance(payload["symbols"], dict):
            for symbol, symbol_cfg in payload["symbols"].items():
                existing = self.draft_config["symbols"].get(symbol, {})
                if isinstance(symbol_cfg, dict):
                    merged = {**existing, **symbol_cfg}
                    self.draft_config["symbols"][symbol] = merged

        if "risk" in payload and isinstance(payload["risk"], dict):
            self.draft_config["risk"] = {**self.draft_config["risk"], **payload["risk"]}

        if "market_structure" in payload and isinstance(payload["market_structure"], dict):
            self.draft_config["market_structure"] = {
                **self.draft_config["market_structure"],
                **payload["market_structure"],
            }

        self._persist_draft()
        logger.info("Draft config updated")
        return self.get_draft()

    def apply_draft(self) -> dict[str, Any]:
        self.active_config = self.get_draft()
        self._write_json(ACTIVE_SYMBOLS_PATH, self.active_config["symbols"])
        self._write_json(ACTIVE_RISK_PATH, self.active_config["risk"])
        self._write_json(ACTIVE_MARKET_STRUCTURE_PATH, self.active_config["market_structure"])
        logger.info("Draft config applied to active config")
        return self.get_active()

    def reset_draft(self) -> dict[str, Any]:
        self.draft_config = self.get_active()
        self._persist_draft()
        logger.info("Draft config reset from active config")
        return self.get_draft()

    def _persist_draft(self) -> None:
        self._write_json(DRAFT_SYMBOLS_PATH, self.draft_config["symbols"])
        self._write_json(DRAFT_RISK_PATH, self.draft_config["risk"])
        self._write_json(DRAFT_MARKET_STRUCTURE_PATH, self.draft_config["market_structure"])


config_manager = ConfigManager()
