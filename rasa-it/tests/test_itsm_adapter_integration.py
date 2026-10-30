"""End-to-end contract tests for the single runtime Rasa ITSM adapter."""
import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from actions.itsm_adapter import ITSMAdapter, IdentityVerificationError

repo_root = Path(__file__).resolve().parents[2]
mock_itsm_dir = repo_root / "mock-itsm-service"

mock_pkg = types.ModuleType("mock_itsm_app")
mock_pkg.__path__ = [str(mock_itsm_dir / "app")]
sys.modules["mock_itsm_app"] = mock_pkg

seed_spec = importlib.util.spec_from_file_location("mock_itsm_app.seed_data", mock_itsm_dir / "app" / "seed_data.py")
seed_mod = importlib.util.module_from_spec(seed_spec)
sys.modules["mock_itsm_app.seed_data"] = seed_mod
seed_spec.loader.exec_module(seed_mod)

main_spec = importlib.util.spec_from_file_location("mock_itsm_app.main", mock_itsm_dir / "app" / "main.py")
main_mod = importlib.util.module_from_spec(main_spec)
sys.modules["mock_itsm_app.main"] = main_mod
main_spec.loader.exec_module(main_mod)
mock_itsm_app = main_mod.app
reset_seed_data = seed_mod.reset_seed_data


@pytest.fixture(autouse=True)
def reset_mock_state():
    reset_seed_data()
    yield
    reset_seed_data()


@pytest.fixture
def mock_transport():
    return ASGITransport(app=mock_itsm_app)


def client_factory(transport):
    return lambda *args, **kwargs: AsyncClient(transport=transport, base_url="http://localhost:9003")


@pytest.mark.asyncio
async def test_seeded_ticket_status_and_unknown_ticket(mock_transport):
    with patch("httpx.AsyncClient", client_factory(mock_transport)):
        result = await ITSMAdapter.get_ticket_status("IT-1001")
        missing = await ITSMAdapter.get_ticket_status("IT-9999")
    assert result["found"] is True
    assert result["status"] == "In Progress"
    assert result["reporter"] == "EMP-1042"
    assert missing["found"] is False


@pytest.mark.asyncio
async def test_create_ticket_then_read_it(mock_transport):
    with patch("httpx.AsyncClient", client_factory(mock_transport)):
        created = await ITSMAdapter.create_ticket("software", "Install editor", "EMP-1042")
        fetched = await ITSMAdapter.get_ticket_status(created["ticket_id"])
    assert created["ticket_id"] == "IT-1004"
    assert fetched["status"] == "Open"
    assert fetched["description"] == "Install editor"


@pytest.mark.asyncio
async def test_verify_identity_then_reset_password(mock_transport):
    with patch("httpx.AsyncClient", client_factory(mock_transport)):
        with pytest.raises(IdentityVerificationError):
            await ITSMAdapter.reset_password("EMP-1042")
        verified = await ITSMAdapter.verify_identity("EMP-1042", "  MYSURU ")
        reset = await ITSMAdapter.reset_password("EMP-1042")
    assert verified["verified"] is True
    assert reset["success"] is True
    assert reset["reset_requested"] is True


@pytest.mark.asyncio
async def test_wrong_answer_does_not_authorize_reset(mock_transport):
    with patch("httpx.AsyncClient", client_factory(mock_transport)):
        result = await ITSMAdapter.verify_identity("EMP-1042", "incorrect")
        with pytest.raises(IdentityVerificationError):
            await ITSMAdapter.reset_password("EMP-1042")
    assert result["verified"] is False
