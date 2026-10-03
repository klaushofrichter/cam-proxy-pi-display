"""Health API answers (schema 1) for the tests. Addresses are documentation ones."""

import json
from pathlib import Path

_DIR = Path(__file__).parent

# generatedAt of every fixture: the tests' "now".
GENERATED_AT_MS = 1791041100000


def load_fixture(name: str) -> dict:
    return json.loads((_DIR / f"{name}.json").read_text())
