"""Handoff types and enums"""

from enum import Enum


class HandoffStatus(str, Enum):
    """Status of a handoff"""

    PENDING = "pending"
    ACCEPTED = "accepted"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


HANDOFF_STATUS_DISPLAY = {
    HandoffStatus.PENDING: "Pending",
    HandoffStatus.ACCEPTED: "Accepted",
    HandoffStatus.COMPLETED: "Completed",
    HandoffStatus.CANCELLED: "Cancelled",
}
