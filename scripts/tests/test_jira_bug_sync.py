import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from jira_bug_sync import issue_key_from_pr, verification_evidence


class VerificationEvidenceTests(unittest.TestCase):
    def test_checked_bug_with_test_evidence_is_accepted(self):
        body = "- [x] SCRUM-51 — test: tests/test_sessions.py::test_slots_reset"
        self.assertEqual(
            verification_evidence(body),
            {"SCRUM-51": "test: tests/test_sessions.py::test_slots_reset"},
        )

    def test_unchecked_bug_is_not_accepted(self):
        body = "- [ ] SCRUM-51 — test: tests/test_sessions.py::test_slots_reset"
        self.assertEqual(verification_evidence(body), {})

    def test_checked_bug_without_evidence_is_not_accepted(self):
        body = "- [x] SCRUM-51 — fixed"
        self.assertEqual(verification_evidence(body), {})

    def test_only_lines_with_explicit_test_evidence_are_accepted(self):
        body = """- [x] SCRUM-51 — test: tests/test_sessions.py::test_slots_reset
- [x] SCRUM-52 — verified by: integration test for outage response
- [x] SCRUM-53 — code changed
"""
        self.assertEqual(
            set(verification_evidence(body)),
            {"SCRUM-51", "SCRUM-52"},
        )

    def test_title_key_takes_precedence_over_body_bug_keys(self):
        self.assertEqual(
            issue_key_from_pr("[SCRUM-42] slice-32-rasa-contract-v2: fix sessions", "- [x] SCRUM-51 — test: test_x"),
            "SCRUM-42",
        )

    def test_body_can_supply_slice_key_if_title_does_not(self):
        self.assertEqual(issue_key_from_pr("fix session slots", "Jira: SCRUM-42"), "SCRUM-42")


if __name__ == "__main__":
    unittest.main()


class Slice38CiGuardrailTests(unittest.TestCase):
    def test_mock_service_matrix_covers_all_mock_backends(self):
        root = Path(__file__).resolve().parents[2]
        workflow = (root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        for service in ("mock-auth-service", "mock-hrms-service", "mock-itsm-service", "mock-admissions-service"):
            self.assertIn(service, workflow)

    def test_rasa_validation_matrix_covers_all_three_role_packs(self):
        root = Path(__file__).resolve().parents[2]
        workflow = (root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        for pack in ("rasa-hr", "rasa-it", "rasa-admissions"):
            self.assertIn(pack, workflow)
        self.assertIn("rasa data validate", workflow)

    def test_pytest_jobs_fail_when_any_tests_are_skipped(self):
        root = Path(__file__).resolve().parents[2]
        workflow = (root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertEqual(workflow.count("--junitxml=pytest-results.xml"), 7)
        self.assertEqual(workflow.count("skipped == 0"), 6)
        self.assertIn("rasa-hr-real-integration", workflow)
        self.assertIn("not test_rasa_data_validate", workflow)


class Slice37ComposeWiringTests(unittest.TestCase):
    def test_compose_wires_it_rasa_action_server_and_tracker_store(self):
        root = Path(__file__).resolve().parents[2]
        compose = (root / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn("rasa-it-actions:", compose)
        self.assertIn("ACTION_ENDPOINT_URL: http://rasa-it-actions:5055/webhook", compose)
        self.assertIn("POSTGRES_HOST: postgres", compose)
        self.assertIn("itsmdata:/data", compose)
        self.assertIn("dockerfile: rasa-it/Dockerfile", compose)
