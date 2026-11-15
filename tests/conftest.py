"""Run from the repository root: python -m pytest tests. With no pytest.ini, this puts the repository root first on
the import path, so the tests always use this copy of the code."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
