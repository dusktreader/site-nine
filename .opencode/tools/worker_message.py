#!/usr/bin/env python3
"""
worker_message tool - Send a message to another active possession.

This tool:
1. Receives from_possession_id, to_possession_id, body, and optional priority/task_id
2. Uses MessageManager.send_conversation_message to deliver the message
3. Returns the conversation ID, message ID, and delivery confirmation
"""

import sys
import json
from tool_logging import logger

from site_nine.core.database import Database
from site_nine.core.paths import get_db_path
from site_nine.messaging import MessageManager
from site_nine.messaging.exceptions import MessagingError, InvalidParticipantError


def main():
    try:
        args = json.loads(sys.stdin.read())

        from_possession_id = args.get("from_possession_id")
        to_possession_id = args.get("to_possession_id")
        body = args.get("body")
        priority = args.get("priority") or "MEDIUM"
        task_id = args.get("task_id")

        if from_possession_id is None:
            return json.dumps({"error": "missing_from_possession_id", "message": "from_possession_id is required."})
        if to_possession_id is None:
            return json.dumps({"error": "missing_to_possession_id", "message": "to_possession_id is required."})
        if not body:
            return json.dumps({"error": "missing_body", "message": "body is required."})

        from_possession_id = int(from_possession_id)
        to_possession_id = int(to_possession_id)

        logger.debug(
            "worker_message_called",
            from_possession_id=from_possession_id,
            to_possession_id=to_possession_id,
            priority=priority,
        )

        db = Database(get_db_path())
        manager = MessageManager(db)

        try:
            conversation, message = manager.send_conversation_message(
                from_possession_id=from_possession_id,
                to_possession_id=to_possession_id,
                body=body,
                priority=priority,
                task_id=task_id,
            )
        except InvalidParticipantError as e:
            logger.warning("worker_message_invalid_participant", error=str(e))
            return json.dumps({"error": "invalid_participant", "message": str(e)})
        except MessagingError as e:
            logger.warning("worker_message_failed", error=str(e))
            return json.dumps({"error": "messaging_error", "message": str(e)})

        logger.info(
            "worker_message_sent",
            conversation_id=conversation.id,
            message_id=message.id,
            from_possession_id=from_possession_id,
            to_possession_id=to_possession_id,
        )

        return json.dumps(
            {
                "conversation_id": conversation.id,
                "message_id": message.id,
                "from_possession_id": from_possession_id,
                "to_possession_id": to_possession_id,
                "priority": str(message.priority),
                "subject": message.subject,
            }
        )

    except Exception as e:
        logger.exception("worker_message_error", error=str(e))
        return json.dumps({"error": "unexpected_error", "message": str(e)})


if __name__ == "__main__":
    print(main())
