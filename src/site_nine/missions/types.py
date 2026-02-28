"""Mission types and constants"""

import inflection
from auto_name_enum import AutoNameEnum, auto


class MissionStatus(AutoNameEnum):
    """
    Lifecycle status of a mission (stored in database).

    Attributes:
        ROLE_PENDING: Mission created, awaiting role selection (ADR-013)
        PERSONA_PENDING: Role set, awaiting persona selection (ADR-013)
        ACTIVE: Mission is running with an agent actively working
        IDLE: Mission has no UNDERWAY tasks and agent is waiting
        SUSPENDED: Mission paused due to session closure (ADR-013)
        ENDED: Mission has been properly dismissed/closed
    """

    ROLE_PENDING = auto()
    PERSONA_PENDING = auto()
    ACTIVE = auto()
    IDLE = auto()
    SUSPENDED = auto()
    ENDED = auto()

    def __str__(self) -> str:
        return inflection.titleize(self.value)
