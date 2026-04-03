#!/usr/bin/env python3
"""
worker_terminate tool - Signal a desk-mode worker to terminate gracefully.

This tool:
1. Receives from_possession_id, to_possession_id, and optional reason
2. Sends a HIGH priority termination message to the target possession via MessageManager
3. The message body instructs the worker to end cleanly using the possession-end skill
4. Returns delivery confirmation
"""

import sys
import json
from tool_logging import logger

from site_nine.core.database import Database
from site_nine.core.paths import get_db_path
from site_nine.messaging import MessageManager
from site_nine.messaging.exceptions import MessagingError, InvalidParticipantError

TERMINATE_BODY_TEMPLATE = """\
**TERMINATION SIGNAL**

You are being asked to terminate gracefully.

{reason_clause}Please complete your current task step (if any), then:
1. Use the `possession-end` skill to close your possession cleanly.
2. Exit your OpenCode session.

Do not start any new tasks.
"""


def main():
    try:
        args = json.loads(sys.stdin.read())

        from_possession_id = args.get("from_possession_id") or args.get("from_mission_id")  # backward compat
        to_possession_id = args.get("to_possession_id") or args.get("to_mission_id")  # backward compat
        reason = args.get("reason")

        if from_possession_id is None:
            return json.dumps({"error": "missing_from_possession_id", "message": "from_possession_id is required."})
        if to_possession_id is None:
            return json.dumps({"error": "missing_to_possession_id", "message": "to_possession_id is required."})

        from_possession_id = int(from_possession_id)
        to_possession_id = int(to_possession_id)

        reason_clause = f"Reason: {reason}\n\n" if reason else ""
        body = TERMINATE_BODY_TEMPLATE.format(reason_clause=reason_clause)

        logger.debug(
            "worker_terminate_called",
            from_possession_id=from_possession_id,
            to_possession_id=to_possession_id,
            has_reason=bool(reason),
        )

        db = Database(get_db_path())
        manager = MessageManager(db)

        try:
            conversation, message = manager.send_conversation_message(
                from_possession_id=from_possession_id,
                to_possession_id=to_possession_id,
                body=body,
                priority="HIGH",
            )
        except InvalidParticipantError as e:
            logger.warning("worker_terminate_invalid_participant", error=str(e))
            return json.dumps({"error": "invalid_participant", "message": str(e)})
        except MessagingError as e:
            logger.warning("worker_terminate_failed", error=str(e))
            return json.dumps({"error": "messaging_error", "message": str(e)})

        logger.info(
            "worker_terminate_signal_sent",
            conversation_id=conversation.id,
            message_id=message.id,
            to_possession_id=to_possession_id,
        )

        return json.dumps(
            {
                "terminated": True,
                "conversation_id": conversation.id,
                "message_id": message.id,
                "from_possession_id": from_possession_id,
                "to_possession_id": to_possession_id,
                "reason": reason,
            }
        )

    except Exception as e:
        logger.exception("worker_terminate_error", error=str(e))
        return json.dumps({"error": "unexpected_error", "message": str(e)})


if __name__ == "__main__":
    print(main())
