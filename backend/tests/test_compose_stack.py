"""Static checks on the repo's docker-compose.yml, the local demo stack (slice-34).

No Docker needed: they parse the file, so CI catches a broken demo setup early.
They live with the backend tests because that CI job has PyYAML installed.
"""
import re
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
COMPOSE_TEXT = (REPO / "docker-compose.yml").read_text(encoding="utf-8")
SERVICES = yaml.safe_load(COMPOSE_TEXT)["services"]
RASA_SERVERS = ["rasa-hr", "rasa-it", "rasa-admissions"]


def test_only_the_frontend_is_reachable_from_other_laptops():
    # B4: clients use port 3000 only; everything else stays on the host laptop.
    for name, service in SERVICES.items():
        if name == "frontend":
            continue
        for port in service.get("ports", []):
            assert str(port).startswith("127.0.0.1:"), f"{name} publishes {port} to the network"
    assert SERVICES["frontend"]["build"]["args"]["NEXT_PUBLIC_API_BASE_URL"] == "/api"


@pytest.mark.parametrize("variable", ["JWT_SECRET", "POSTGRES_PASSWORD"])
def test_secrets_have_no_hardcoded_defaults(variable):
    assert f"${{{variable}:-" not in COMPOSE_TEXT
    assert f"${{{variable}:?" in COMPOSE_TEXT


@pytest.mark.parametrize("service", RASA_SERVERS)
def test_each_rasa_server_sets_every_variable_its_endpoints_file_uses(service):
    lines = (REPO / service / "endpoints.yml").read_text(encoding="utf-8").splitlines()
    needed = {var for line in lines if not line.lstrip().startswith("#") for var in re.findall(r"\$\{(\w+)\}", line)}
    env = SERVICES[service]["environment"]

    assert needed and needed <= set(env)
    assert env["POSTGRES_DB"] == service.replace("-", "_")
    assert env["ACTION_ENDPOINT_URL"] == f"http://{service}-actions:5055/webhook"


@pytest.mark.parametrize("service", RASA_SERVERS)
def test_each_action_server_runs_from_its_packs_image(service):
    actions = SERVICES[f"{service}-actions"]

    assert actions["image"] == SERVICES[service]["image"]
    assert actions["command"][:2] == ["run", "actions"]
