"""Gemeinsame Hilfsfunktionen: Pfade, Konfiguration, Hashes, Git-Stand, Protokollierung."""

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml

RAG_DIR = Path(__file__).resolve().parent
ROOT = RAG_DIR.parent                      # Repo-Hauptverzeichnis (kb/, tickets.jsonl)
CONFIG_FILE = RAG_DIR / "config.yaml"
DATA_DIR = RAG_DIR / "data"
LOG_DIR = RAG_DIR / "logs"


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def load_config() -> dict:
    with CONFIG_FILE.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def config_hash(cfg: dict) -> str:
    return sha256(json.dumps(cfg, sort_keys=True, ensure_ascii=False))


def kb_hash(kb_dir: Path) -> str:
    """Gleiche Berechnung wie in generate_tickets.py: Der Wert muss mit meta.kb_hash der Tickets übereinstimmen."""
    files = sorted(kb_dir.glob("KB-*.md"))
    parts = [f'<artikel id="{p.stem}">\n{p.read_text(encoding="utf-8").strip()}\n</artikel>' for p in files]
    return sha256("\n\n".join(parts))


def git_info() -> dict:
    """Commit und ob es nicht committete Änderungen gibt; belegt, mit welchem Code-Stand ein Lauf erfolgte."""
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip())
        return {"commit": commit, "dirty": dirty}
    except (OSError, subprocess.CalledProcessError):
        return {"commit": None, "dirty": None}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def append_jsonl(path: Path, entry: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def cost_usd(cfg: dict, model: str, input_tokens: int = 0, output_tokens: int = 0, cached_tokens: int = 0) -> float:
    """Kosten nach Preisliste zum Stichtag (config.yaml); cached_tokens sind ein Teil der input_tokens."""
    p = cfg["preise_usd_pro_1m_tokens"][model]
    uncached = input_tokens - cached_tokens
    cost = uncached * p["input"] + cached_tokens * p.get("cached_input", p["input"]) + output_tokens * p.get("output", 0)
    return round(cost / 1_000_000, 8)
