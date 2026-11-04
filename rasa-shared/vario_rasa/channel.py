"""Custom Rasa input channel serving the VARIO converse endpoint (ADR-006).

Register it in a role pack's credentials.yml:

    vario_rasa.channel.VarioInputChannel: {}

Rasa then serves POST /webhooks/vario/converse. Each request is one user turn;
the response is built from the turn's tracker state and collected bot messages.
"""
import logging
from typing import Any, Awaitable, Callable, Text

from rasa.core.channels.channel import CollectingOutputChannel, InputChannel, UserMessage
from rasa.shared.core.events import UserUttered
from rasa.shared.core.trackers import DialogueStateTracker
from sanic import Blueprint, response
from sanic.request import Request
from sanic.response import HTTPResponse

from vario_rasa.contract import build_converse_response, validate_converse_request

logger = logging.getLogger(__name__)


def _this_turn(tracker: DialogueStateTracker) -> UserUttered:
    """The user message just handled.

    Not `tracker.latest_message`: a tracker loaded from the store replays only its
    "applied" events, and Rasa folds each happy-path form turn into the previous form
    run, so `latest_message` would still be the message that started the form.
    """
    for event in reversed(tracker.events):
        if isinstance(event, UserUttered):
            return event
    return UserUttered.empty()


class VarioInputChannel(InputChannel):
    """POST /webhooks/vario/converse — the gateway's single entry into a role pack."""

    @classmethod
    def name(cls) -> Text:
        return "vario"

    def blueprint(self, on_new_message: Callable[[UserMessage], Awaitable[Any]]) -> Blueprint:
        webhook = Blueprint("vario_webhook", __name__)

        @webhook.route("/", methods=["GET"])
        async def health(_: Request) -> HTTPResponse:
            return response.json({"status": "ok"})

        @webhook.route("/converse", methods=["POST"])
        async def converse(request: Request) -> HTTPResponse:
            body = request.json
            error = validate_converse_request(body)
            if error:
                return response.json({"error": error}, status=400)

            sender = body["sender"]
            collector = CollectingOutputChannel()
            await on_new_message(
                UserMessage(
                    body["message"],
                    collector,
                    sender,
                    input_channel=self.name(),
                    metadata=body.get("metadata") or {},
                )
            )

            tracker = await request.app.ctx.agent.tracker_store.retrieve(sender)
            payload = build_converse_response(
                parse_data=_this_turn(tracker).parse_data,
                active_loop=tracker.active_loop_name,
                requested_slot=tracker.get_slot("requested_slot"),
                bot_messages=collector.messages,
            )
            # Intent and form only — never message text or slot values.
            logger.info(
                "vario converse intent=%s confidence=%.2f form=%s step=%s",
                payload["intent"],
                payload["confidence"],
                payload["current_form"],
                payload["current_step"],
            )
            return response.json(payload)

        return webhook
