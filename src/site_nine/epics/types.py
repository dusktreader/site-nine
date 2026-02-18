"""Epic types and constants"""

import inflection
from auto_name_enum import AutoNameEnum, auto


class EpicStatus(AutoNameEnum):
    """
    Computed status of an epic (derived from subtask states, not stored in DB).

    Attributes:
        TODO: No tasks started (or no tasks)
        UNDERWAY: At least one task is in progress or complete (but not all terminal)
        COMPLETE: All tasks are complete
        ABORTED: All tasks are terminal and at least one is aborted
    """

    TODO = auto()
    UNDERWAY = auto()
    COMPLETE = auto()
    ABORTED = auto()

    def __str__(self) -> str:
        return inflection.titleize(self.value)
