#!/usr/bin/env python3
"""
watch_inbox tool - Block until a new message arrives or timeout expires.

This tool:
1. Receives mission_id and optional timeout (seconds, default 300)
2. Polls for unread messages every poll_interval seconds (default 5)
3. Returns immediately when a new message arrives
4. Returns a timeout result if no message arrives within timeout seconds

Designed for Admin/Orchestrator agents to sleep efficiently between worker
callbacks instead of busy-polling on a fixed schedule.
"""

import sys
import json
import time
from loguru import logger

from site_nine.core.database import Database
from site_nine.core.paths import get_db_path
from site_nine.messaging import MessageManager


def main():
    try:
        args = json.loads(sys.stdin.read())

        mission_id = args.get("mission_id")
        timeout = int(args.get("timeout") or 300)
        poll_interval = int(args.get("poll_interval") or 5)

        if mission_id is None:
            return json.dumps({"error": "missing_mission_id", "message": "mission_id is required."})

        mission_id = int(mission_id)

        logger.debug("watch_inbox_called", mission_id=mission_id, timeout=timeout, poll_interval=poll_interval)

        db = Database(get_db_path())
        manager = MessageManager(db)

        deadline = time.time() + timeout
        elapsed = 0

        while time.time() < deadline:
            unread_convs = manager.get_unread_conversations(mission_id)

            if unread_convs:
                # Collect all unread messages across all conversations
                messages = []
                for conv in unread_convs:
                    unread = manager.get_unread_messages(conv.id, mission_id)
                    for msg in unread:
                        # Only include messages FROM others (not own messages)
                        if msg.from_mission_id != mission_id:
                            messages.append(
                                {
                                    "message_id": msg.id,
                                    "conversation_id": msg.conversation_id,
                                    "from_mission_id": msg.from_mission_id,
                                    "subject": msg.subject,
                                    "body": msg.body,
                                    "priority": str(msg.priority),
                                    "created_at": str(msg.created_at),
                                }
                            )

                if messages:
                    # Acknowledge all returned messages so they are not replayed
                    acked_conversations: set[str] = set()
                    for m in messages:
                        manager.acknowledge_message(m["message_id"], mission_id)
                        acked_conversations.add(m["conversation_id"])
                    for conv_id in acked_conversations:
                        manager.update_conversation_view(conv_id, mission_id)

                    logger.info("watch_inbox_message_received", mission_id=mission_id, count=len(messages))
                    return json.dumps(
                        {
                            "status": "message_received",
                            "mission_id": mission_id,
                            "message_count": len(messages),
                            "messages": messages,
                            "elapsed_seconds": int(time.time() - (deadline - timeout)),
                        }
                    )

            time.sleep(poll_interval)
            elapsed = int(time.time() - (deadline - timeout))

        logger.info("watch_inbox_timeout", mission_id=mission_id, timeout=timeout)
        return json.dumps(
            {
                "status": "timeout",
                "mission_id": mission_id,
                "message_count": 0,
                "messages": [],
                "elapsed_seconds": elapsed,
            }
        )

    except Exception as e:
        logger.exception("watch_inbox_error", error=str(e))
        return json.dumps({"error": "unexpected_error", "message": str(e)})


if __name__ == "__main__":
    print(main())
