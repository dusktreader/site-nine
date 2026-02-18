"""Mission types and constants"""

import inflection
from auto_name_enum import AutoNameEnum, auto


class MissionStatus(AutoNameEnum):
    """
    Lifecycle status of a mission (stored in database).

    Attributes:
        ACTIVE: Mission is running with an agent actively working
        IDLE: Mission has no UNDERWAY tasks and agent is waiting
        ENDED: Mission has been properly dismissed/closed
    """

    ACTIVE = auto()
    IDLE = auto()
    ENDED = auto()

    def __str__(self) -> str:
        return inflection.titleize(self.value)
