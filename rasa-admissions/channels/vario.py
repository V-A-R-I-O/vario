import logging
from typing import Dict, Text, Any, Callable, Awaitable
from aiohttp import web

logger = logging.getLogger(__name__)

try:
    from rasa.core.channels.channel import InputChannel, OutputChannel, UserMessage
    HAS_RASA_CORE = True
except ImportError:
    HAS_RASA_CORE = False

    class InputChannel:  # type: ignore
        pass

    class OutputChannel:  # type: ignore
        pass


class VarioInputChannel(InputChannel):
    """
    Rasa custom input channel for VARIO dialogue router (see ADR-002).
    Mounts route: POST /webhooks/vario/converse
    """

    @classmethod
    def name(cls) -> Text:
        return "vario"

    def url_prefix(self) -> Text:
        return "vario"

    def blueprint(
        self, on_new_message: Callable[[Any], Awaitable[Any]]
    ) -> Any:
        custom_webhook = web.RouteTableDef()

        @custom_webhook.post("/converse")
        async def converse_webhook(request: web.Request) -> web.Response:
            payload = await request.json()
            sender_id = payload.get("sender")
            text = payload.get("message")
            session = payload.get("session", {})

            logger.info("Received converse request from sender=%s: %s", sender_id, text)
            # Response contract shape per ADR-002
            response_payload = {
                "intent": "check_application_status",
                "confidence": 0.95,
                "entities": {},
                "template_key": "check_application_status_response",
                "slots": {},
                "current_form": None,
                "current_step": None,
                "response_text": None,
            }
            return web.json_response(response_payload)

        return custom_webhook
