"""Handoff types and enums"""

import inflection
from auto_name_enum import AutoNameEnum, LowerCaseMixin, auto


class HandoffStatus(AutoNameEnum, LowerCaseMixin):
    """
    Status of a handoff

    Attributes:
        PENDING: Handoff created, awaiting acceptance
        ACCEPTED: Handoff accepted, work in progress
        COMPLETED: Handoff work finished successfully
        CANCELLED: Handoff cancelled before completion
    """

    PENDING = auto()
    ACCEPTED = auto()
    COMPLETED = auto()
    CANCELLED = auto()

    def __str__(self) -> str:
        return inflection.titleize(self.value)
