from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4


@dataclass(frozen=True)
class Paths:
    root: Path
    templates: Path
    documents: Path
    charts: Path


def get_paths() -> Paths:
    root = Path(os.environ.get("DOCPILOT_DATA_DIR", Path(__file__).resolve().parents[3] / "backend" / ".data"))
    templates = root / "templates"
    documents = root / "documents"
    charts = root / "charts"
    templates.mkdir(parents=True, exist_ok=True)
    documents.mkdir(parents=True, exist_ok=True)
    charts.mkdir(parents=True, exist_ok=True)
    return Paths(root=root, templates=templates, documents=documents, charts=charts)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def read_json(path: Path) -> Optional[Any]:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
