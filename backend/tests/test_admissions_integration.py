import pytest
import sys
import types
import importlib.util
from pathlib import Path
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch

# Load mock-admissions-service in an isolated namespace to avoid collision with backend app
repo_root = Path(__file__).resolve().parent.parent.parent
mock_adm_dir = repo_root / "mock-admissions-service"

mock_pkg = types.ModuleType("mock_admissions_app")
sys.modules["mock_admissions_app"] = mock_pkg

seed_spec = importlib.util.spec_from_file_location(
    "mock_admissions_app.seed_data", mock_adm_dir / "app" / "seed_data.py"
)
seed_mod = importlib.util.module_from_spec(seed_spec)
sys.modules["mock_admissions_app.seed_data"] = seed_mod
seed_spec.loader.exec_module(seed_mod)

main_spec = importlib.util.spec_from_file_location(
    "mock_admissions_app.main", mock_adm_dir / "app" / "main.py"
)
main_mod = importlib.util.module_from_spec(main_spec)
sys.modules["mock_admissions_app.main"] = main_mod
main_spec.loader.exec_module(main_mod)
mock_admissions_app = main_mod.app

from app.services.admissions_adapter import (
    AdmissionsAdapter,
    ApplicationNotFoundError,
    ProgramNotFoundError,
)


@pytest.fixture
def mock_asgi_transport():
    return ASGITransport(app=mock_admissions_app)


@pytest.mark.asyncio
async def test_integration_seeded_application_status(mock_asgi_transport):
    """
    AC 2: Given a seeded application_id, when get_application_status is called,
    then it returns status + a suggested next step via real integration.
    """
    with patch(
        "httpx.AsyncClient",
        lambda *args, **kwargs: AsyncClient(
            transport=mock_asgi_transport, base_url="http://localhost:9004"
        ),
    ):
        # 1. Under Review application
        res1 = await AdmissionsAdapter.get_application_status("APP-1001")
        assert res1["found"] is True
        assert res1["application_id"] == "APP-1001"
        assert res1["applicant_name"] == "Aarav Sharma"
        assert res1["status"] == "Under Review"
        assert (
            "evaluation" in res1["next_step"].lower()
            or "committee" in res1["next_step"].lower()
            or "results" in res1["next_step"].lower()
        )

        # 2. Accepted application
        res2 = await AdmissionsAdapter.get_application_status("APP-1002")
        assert res2["found"] is True
        assert res2["status"] == "Accepted"
        assert "50,000" in res2["next_step"] or "deposit" in res2["next_step"].lower()

        # 3. Documents pending
        res3 = await AdmissionsAdapter.get_application_status("APP-1003")
        assert res3["found"] is True
        assert res3["status"] == "Documents Pending"
        assert (
            "marksheet" in res3["next_step"].lower()
            or "certificate" in res3["next_step"].lower()
            or "portal" in res3["next_step"].lower()
        )


@pytest.mark.asyncio
async def test_integration_unknown_application_id(mock_asgi_transport):
    """
    AC 3: Given an unknown application_id, then the adapter returns a not-found
    result carrying a suggested next step (supports FR-17).
    """
    with patch(
        "httpx.AsyncClient",
        lambda *args, **kwargs: AsyncClient(
            transport=mock_asgi_transport, base_url="http://localhost:9004"
        ),
    ):
        res = await AdmissionsAdapter.get_application_status("APP-9999")
        assert res["found"] is False
        assert res["application_id"] == "APP-9999"
        assert res["status"] == "Not Found"
        assert "admissions@org.example.com" in res["suggested_next_step"]


@pytest.mark.asyncio
async def test_integration_unknown_application_id_raises_when_requested(
    mock_asgi_transport,
):
    with patch(
        "httpx.AsyncClient",
        lambda *args, **kwargs: AsyncClient(
            transport=mock_asgi_transport, base_url="http://localhost:9004"
        ),
    ):
        with pytest.raises(ApplicationNotFoundError) as exc_info:
            await AdmissionsAdapter.get_application_status(
                "APP-9999", raise_for_not_found=True
            )

        assert exc_info.value.application_id == "APP-9999"
        assert "admissions@org.example.com" in exc_info.value.suggested_next_step


@pytest.mark.asyncio
async def test_integration_document_checklist(mock_asgi_transport):
    """
    AC 5: Given the adapter, then get_document_checklist is implemented and callable.
    """
    with patch(
        "httpx.AsyncClient",
        lambda *args, **kwargs: AsyncClient(
            transport=mock_asgi_transport, base_url="http://localhost:9004"
        ),
    ):
        res = await AdmissionsAdapter.get_document_checklist("btech")
        assert res["found"] is True
        assert res["program"] == "Computer Science (B.Tech)"
        assert len(res["required_documents"]) >= 3


@pytest.mark.asyncio
async def test_integration_calendar(mock_asgi_transport):
    """
    AC 5: Given the adapter, then get_calendar is implemented and callable.
    """
    with patch(
        "httpx.AsyncClient",
        lambda *args, **kwargs: AsyncClient(
            transport=mock_asgi_transport, base_url="http://localhost:9004"
        ),
    ):
        cal = await AdmissionsAdapter.get_calendar()
        assert cal["academic_year"] == "2026-2027"
        assert len(cal["deadlines"]) >= 3
        assert len(cal["fees"]) >= 3
        assert "refund_policy" in cal
