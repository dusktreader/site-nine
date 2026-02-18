"""Review types and constants"""

import inflection
from auto_name_enum import AutoNameEnum, LowerCaseMixin, auto


class ReviewType(AutoNameEnum, LowerCaseMixin):
    """
    Types of reviews that can be requested

    Attributes:
        CODE: Review of code implementation and quality
        TASK_COMPLETION: Review to verify task completion criteria met
        DESIGN: Review of design documents or architecture
        GENERAL: General purpose review not fitting other categories
    """

    CODE = auto()
    TASK_COMPLETION = auto()
    DESIGN = auto()
    GENERAL = auto()

    def __str__(self) -> str:
        return inflection.titleize(self.value)


class ReviewOutcome(AutoNameEnum, LowerCaseMixin):
    """
    Outcome of a review

    Attributes:
        PENDING: Review requested, awaiting completion
        APPROVED: Review completed and approved
        REJECTED: Review completed but rejected
    """

    PENDING = auto()
    APPROVED = auto()
    REJECTED = auto()

    def __str__(self) -> str:
        return inflection.titleize(self.value)


# Backward compatibility alias
ReviewStatus = ReviewOutcome
