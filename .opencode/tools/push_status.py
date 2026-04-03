#!/usr/bin/env python3
"""
push_status - Push a status message to the director's toast queue.

Use this tool to let the director know what you're doing without sending a full
message. Status messages appear as toast notifications in the TUI. Keep them
short and informative.

Input (JSON via stdin):
    possession_id: int - Your possession ID
    message:       str - Short status message (ideally under 120 chars)

Output (JSON via stdout):
    {"status": "ok", "id": <int>}
    {"status": "error", "message": <str>}
"""

import sys
import json
from tool_logging import logger

from site_nine.core.database import Database
from site_nine.core.paths import get_db_path


def main() -> str:
    try:
        data = json.loads(sys.stdin.read())
        possession_id = int(data["possession_id"])
        message = str(data["message"]).strip()

        if not message:
            return json.dumps({"status": "error", "message": "message cannot be empty"})

        db_path = get_db_path()
        db = Database(db_path)

        row_id = db.execute_insert(
            "INSERT INTO status_queue (possession_id, message) VALUES (:possession_id, :message)",
            {"possession_id": possession_id, "message": message},
        )

        logger.info("push_status_ok", possession_id=possession_id, queue_id=row_id, message=message)
        return json.dumps({"status": "ok", "id": row_id})

    except Exception as e:
        logger.exception("push_status_error", error=str(e))
        return json.dumps({"status": "error", "message": str(e)})


if __name__ == "__main__":
    print(main())
