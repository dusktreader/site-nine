"""Task types and constants"""

import inflection
from auto_name_enum import AutoNameEnum, auto


class TaskStatus(AutoNameEnum):
    """
    Work status of a task (stored in database)

    Attributes:
        TODO: Task not yet started
        UNDERWAY: Task actively being worked on
        COMPLETE: Task finished successfully
        ABORTED: Task cancelled or abandoned
    """

    TODO = auto()
    UNDERWAY = auto()
    COMPLETE = auto()
    ABORTED = auto()

    def __str__(self) -> str:
        return inflection.titleize(self.value)


class EffectiveStatus(AutoNameEnum):
    """
    Effective status of a task (computed from work status + blocking reasons)

    Attributes:
        TODO: Task not yet started
        UNDERWAY: Task actively being worked on
        COMPLETE: Task finished successfully
        ABORTED: Task cancelled or abandoned
        BLOCKED_EXTERNAL: Task blocked by external dependency
        BLOCKED_DEPENDENCY: Task blocked by internal task dependency
        BLOCKED_REVIEW: Task blocked awaiting review approval
    """

    TODO = auto()
    UNDERWAY = auto()
    COMPLETE = auto()
    ABORTED = auto()
    BLOCKED_EXTERNAL = auto()
    BLOCKED_DEPENDENCY = auto()
    BLOCKED_REVIEW = auto()

    def __str__(self) -> str:
        return inflection.titleize(self.value)
