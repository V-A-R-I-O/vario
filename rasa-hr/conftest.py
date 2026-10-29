import sys
from pathlib import Path

HR_DIR = Path(__file__).resolve().parent
REPO_ROOT = HR_DIR.parent
RASA_SHARED = REPO_ROOT / "rasa-shared"

for p in [HR_DIR, RASA_SHARED]:
    if p.exists() and str(p) not in sys.path:
        sys.path.insert(0, str(p))
