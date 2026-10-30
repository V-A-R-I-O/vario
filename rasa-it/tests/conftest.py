import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SHARED = REPO_ROOT / "rasa-shared"
if str(SHARED) not in sys.path:
    sys.path.insert(0, str(SHARED))
