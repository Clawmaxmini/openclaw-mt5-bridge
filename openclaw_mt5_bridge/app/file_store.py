import csv
import json
from pathlib import Path
from typing import Any


class FileStoreError(Exception):
    pass


class FileMalformedError(FileStoreError):
    pass


class FileStore:
    def resolve_path(self, base_dir: str, filename: str) -> Path:
        return Path(base_dir) / filename

    def exists(self, path: Path) -> bool:
        return path.exists()

    def read_json(self, path: Path) -> dict[str, Any]:
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as exc:
            raise FileMalformedError(f"Malformed JSON file: {path}") from exc
        except OSError as exc:
            raise FileStoreError(f"Failed to read file: {path}") from exc

    def read_jsonl(self, path: Path) -> list[dict[str, Any]]:
        try:
            rows: list[dict[str, Any]] = []
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rows.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            return rows
        except OSError as exc:
            raise FileStoreError(f"Failed to read file: {path}") from exc

    def read_csv(self, path: Path) -> list[dict[str, str]]:
        try:
            with path.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                return [dict(row) for row in reader]
        except OSError as exc:
            raise FileStoreError(f"Failed to read CSV: {path}") from exc

    def write_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with path.open("w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except OSError as exc:
            raise FileStoreError(f"Failed to write JSON: {path}") from exc

    def append_jsonl(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except OSError as exc:
            raise FileStoreError(f"Failed to append JSONL: {path}") from exc


file_store = FileStore()
