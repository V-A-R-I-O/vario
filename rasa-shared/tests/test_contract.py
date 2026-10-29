"""Pure-Python tests for vario_rasa.contract (no Rasa install needed)."""
import json

import pytest

from tests.conftest import CONTRACT_DIR
from vario_rasa.contract import (
    CARD_TYPES,
    build_converse_response,
    entities_to_dict,
    is_valid_card,
    validate_converse_request,
    vario_payload,
)

RESPONSE_FIXTURES = [
    "converse-response-card-turn.json",
    "converse-response-form-turn.json",
    "converse-response-sensitive-turn.json",
]


def _fixture(name):
    return json.loads((CONTRACT_DIR / name).read_text(encoding="utf-8"))


def _parse(name="check_leave_balance", confidence=0.93, entities=None):
    return {"intent": {"name": name, "confidence": confidence}, "entities": entities or []}


def test_card_types_match_frontend_fixture():
    assert CARD_TYPES == frozenset(_fixture("card-types.json"))


def test_vario_payload_omits_unset_fields():
    assert vario_payload(template_key="t") == {"vario": {"template_key": "t"}}
    assert vario_payload(sensitive_next_input=True) == {"vario": {"sensitive_next_input": True}}


def test_vario_payload_rejects_unknown_card_type():
    with pytest.raises(ValueError):
        vario_payload(card={"type": "leave_balance_card"})


def test_text_and_vario_payload_combine_into_one_response():
    result = build_converse_response(
        parse_data=_parse(),
        active_loop=None,
        requested_slot=None,
        bot_messages=[
            {"text": "Here is your balance."},
            {"custom": vario_payload(template_key="k", slots={"total": 2}, card={"type": "data_card", "rows": []})},
        ],
    )
    assert result["response_text"] == "Here is your balance."
    assert result["template_key"] == "k"
    assert result["slots"] == {"total": 2}
    assert result["card"]["type"] == "data_card"
    assert result["intent"] == "check_leave_balance"
    assert result["confidence"] == pytest.approx(0.93)


def test_response_has_exactly_the_contract_fields():
    result = build_converse_response(parse_data=_parse(), active_loop=None, requested_slot=None, bot_messages=[])
    assert set(result) == set(_fixture("converse-response-card-turn.json"))


def test_multiple_texts_are_joined_and_last_payload_wins():
    result = build_converse_response(
        parse_data=_parse(),
        active_loop=None,
        requested_slot=None,
        bot_messages=[
            {"text": "One."},
            {"custom": vario_payload(template_key="first")},
            {"text": "Two."},
            {"custom": vario_payload(template_key="second")},
        ],
    )
    assert result["response_text"] == "One.\n\nTwo."
    assert result["template_key"] == "second"


def test_buttons_become_a_slot_prompt_card():
    result = build_converse_response(
        parse_data=_parse("submit_leave_request"),
        active_loop="leave_request_form",
        requested_slot="leave_type",
        bot_messages=[{"text": "Which type?", "buttons": [{"title": "Sick", "payload": "sick"}]}],
    )
    assert result["card"] == {
        "type": "slot_prompt",
        "text": "Which type?",
        "options": [{"label": "Sick", "value": "sick"}],
    }
    assert result["current_form"] == "leave_request_form"
    assert result["current_step"] == "leave_type"


def test_invalid_card_is_dropped():
    result = build_converse_response(
        parse_data=_parse(),
        active_loop=None,
        requested_slot=None,
        bot_messages=[{"custom": {"vario": {"card": {"type": "made_up"}}}}],
    )
    assert result["card"] is None


def test_requested_slot_is_ignored_without_an_active_form():
    result = build_converse_response(parse_data=_parse(), active_loop=None, requested_slot="leave_type", bot_messages=[])
    assert result["current_step"] is None


def test_sensitive_flag_is_reported():
    result = build_converse_response(
        parse_data=_parse("reset_password"),
        active_loop="reset_password_form",
        requested_slot="security_answer",
        bot_messages=[{"text": "Security question?"}, {"custom": vario_payload(sensitive_next_input=True)}],
    )
    assert result["sensitive_next_input"] is True


def test_entities_to_dict_keeps_last_value():
    ents = [{"entity": "leave_type", "value": "sick"}, {"entity": "leave_type", "value": "casual"}]
    assert entities_to_dict(ents) == {"leave_type": "casual"}


@pytest.mark.parametrize(
    "body, ok",
    [
        ({"sender": "c1", "message": "hi"}, True),
        ({"sender": "c1", "message": "hi", "metadata": {}}, True),
        ({"sender": "", "message": "hi"}, False),
        ({"sender": "c1", "message": "   "}, False),
        ({"sender": "c1", "message": "hi", "metadata": "x"}, False),
        ([], False),
    ],
)
def test_validate_converse_request(body, ok):
    assert (validate_converse_request(body) is None) == ok


def test_request_fixture_is_valid():
    assert validate_converse_request(_fixture("converse-request.json")) is None


@pytest.mark.parametrize("name", RESPONSE_FIXTURES)
def test_response_fixtures_follow_the_contract(name):
    payload = _fixture(name)
    assert set(payload) == set(_fixture("converse-response-card-turn.json"))
    assert payload["card"] is None or is_valid_card(payload["card"])
