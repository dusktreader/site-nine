"""ADR types and constants"""

import inflection
from auto_name_enum import AutoNameEnum, auto


class ADRStatus(AutoNameEnum):
    """
    Status of an Architecture Decision Record

    Attributes:
        PROPOSED: Decision proposed, under discussion
        ACCEPTED: Decision accepted and in effect
        REJECTED: Decision rejected
        SUPERSEDED: Replaced by a newer decision
        DEPRECATED: No longer recommended but not formally superseded
    """

    PROPOSED = auto()
    ACCEPTED = auto()
    REJECTED = auto()
    SUPERSEDED = auto()
    DEPRECATED = auto()

    def __str__(self) -> str:
        return inflection.titleize(self.value)
