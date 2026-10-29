import sys
from pathlib import Path

RASA_SHARED = Path(__file__).resolve().parents[1]
CONTRACT_DIR = RASA_SHARED / "contract"

if str(RASA_SHARED) not in sys.path:
    sys.path.insert(0, str(RASA_SHARED))
