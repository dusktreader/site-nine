"""Review types and constants"""

from enum import Enum


class ReviewType(str, Enum):
    """Types of reviews that can be requested"""

    CODE = "code"
    TASK_COMPLETION = "task_completion"
    DESIGN = "design"
    GENERAL = "general"


class ReviewStatus(str, Enum):
    """Status of a review"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


# Display names for review types
REVIEW_TYPE_DISPLAY = {
    ReviewType.CODE: "Code/PR Review",
    ReviewType.TASK_COMPLETION: "Task Completion Review",
    ReviewType.DESIGN: "Design/Architecture Review",
    ReviewType.GENERAL: "General Artifact Review",
}
