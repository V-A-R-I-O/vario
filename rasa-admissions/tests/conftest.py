import sys
from pathlib import Path
import pytest
import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MOCK_SERVICE_DIR = REPO_ROOT / "mock-admissions-service"
RASA_ADM_DIR = REPO_ROOT / "rasa-admissions"

if str(MOCK_SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(MOCK_SERVICE_DIR))
if str(RASA_ADM_DIR) not in sys.path:
    sys.path.insert(0, str(RASA_ADM_DIR))

from app.main import app as mock_admissions_app
from actions.admissions_adapter import AdmissionsAdapter


@pytest.fixture(autouse=True)
def configure_mock_admissions():
    AdmissionsAdapter._transport = httpx.ASGITransport(app=mock_admissions_app)
    yield
    AdmissionsAdapter._transport = None
