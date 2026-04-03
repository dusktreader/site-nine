"""Possession types and constants"""

import inflection
from auto_name_enum import AutoNameEnum, auto


class PossessionStatus(AutoNameEnum):
    """
    Lifecycle status of a possession (stored in database).

    Attributes:
        ROLE_PENDING: Possession created, awaiting role selection
        DAEMON_PENDING: Role set, awaiting daemon selection
        ACTIVE: Possession is running with an agent actively working
        SUSPENDED: Possession paused due to session closure
        EXORCISED: Possession has been properly dismissed/closed
    """

    ROLE_PENDING = auto()
    DAEMON_PENDING = auto()
    ACTIVE = auto()
    SUSPENDED = auto()
    EXORCISED = auto()

    def __str__(self) -> str:
        return inflection.titleize(self.value)
