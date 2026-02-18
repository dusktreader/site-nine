"""Tests for reviews manager"""

import pytest

from site_nine.core.database import Database
from site_nine.reviews.exceptions import ReviewError
from site_nine.reviews.manager import ReviewManager
from site_nine.reviews.types import ReviewOutcome, ReviewType


def test_review_manager_create_review_basic(test_db_with_data):
    """Test creating a basic review"""
    manager = ReviewManager(test_db_with_data)

    review_id = manager.create_review(
        type="code", title="Review PR #123", description="Please review the authentication changes"
    )

    assert review_id > 0

    # Verify review was created
    review = manager.get_review(review_id)
    assert review is not None
    assert review.type == "code"
    assert review.title == "Review PR #123"
    assert review.description == "Please review the authentication changes"
    assert review.outcome == "pending"


def test_review_manager_create_review_with_task(test_db_with_data):
    """Test creating review associated with a task"""
    manager = ReviewManager(test_db_with_data)

    review_id = manager.create_review(
        type="task_completion",
        title="Task completion review",
        description="Review completed task",
        task_id="ENG-M-0001",
    )

    review = manager.get_review(review_id)
    assert review.task_id == "ENG-M-0001"


def test_review_manager_create_review_with_enum(test_db_with_data):
    """Test creating review using ReviewType enum"""
    manager = ReviewManager(test_db_with_data)

    review_id = manager.create_review(type=ReviewType.DESIGN, title="Design review", description="Review API design")

    review = manager.get_review(review_id)
    assert review.type == "design"


def test_review_manager_create_review_with_metadata(test_db_with_data):
    """Test creating review with all optional fields"""
    manager = ReviewManager(test_db_with_data)

    review_id = manager.create_review(
        type="code",
        title="Code review",
        description="Review changes",
        task_id="ENG-M-0001",
        requested_by="test-persona",
        artifact_path="/path/to/code.py",
    )

    review = manager.get_review(review_id)
    assert review.requested_by == "test-persona"
    assert review.artifact_path == "/path/to/code.py"


def test_review_manager_get_review_not_found(test_db_with_data):
    """Test getting non-existent review returns None"""
    manager = ReviewManager(test_db_with_data)

    review = manager.get_review(999)

    assert review is None


def test_review_manager_list_reviews_empty(test_db_with_data):
    """Test listing reviews when none exist"""
    manager = ReviewManager(test_db_with_data)

    reviews = manager.list_reviews()

    assert reviews == []


def test_review_manager_list_reviews(test_db_with_data):
    """Test listing all reviews"""
    manager = ReviewManager(test_db_with_data)

    id1 = manager.create_review("code", "Review 1", "Description 1")
    id2 = manager.create_review("design", "Review 2", "Description 2")

    reviews = manager.list_reviews()

    assert len(reviews) == 2
    review_ids = {r.id for r in reviews}
    assert review_ids == {id1, id2}


def test_review_manager_list_reviews_by_type(test_db_with_data):
    """Test filtering reviews by type"""
    manager = ReviewManager(test_db_with_data)

    manager.create_review("code", "Code review 1", "Desc 1")
    manager.create_review("design", "Design review", "Desc 2")
    manager.create_review("code", "Code review 2", "Desc 3")

    code_reviews = manager.list_reviews(type="code")

    assert len(code_reviews) == 2
    assert all(r.type == "code" for r in code_reviews)


def test_review_manager_list_reviews_by_type_enum(test_db_with_data):
    """Test filtering reviews by type using enum"""
    manager = ReviewManager(test_db_with_data)

    manager.create_review(ReviewType.CODE, "Review 1", "Desc 1")
    manager.create_review(ReviewType.DESIGN, "Review 2", "Desc 2")

    code_reviews = manager.list_reviews(type=ReviewType.CODE)

    assert len(code_reviews) == 1
    assert code_reviews[0].type == "code"


def test_review_manager_list_reviews_by_outcome(test_db_with_data):
    """Test filtering reviews by outcome"""
    manager = ReviewManager(test_db_with_data)

    id1 = manager.create_review("code", "Review 1", "Desc 1")
    manager.create_review("code", "Review 2", "Desc 2")

    # Approve one review
    manager.approve_review(id1, "Director", "Looks good")

    pending_reviews = manager.list_reviews(outcome="pending")
    approved_reviews = manager.list_reviews(outcome="approved")

    assert len(pending_reviews) == 1
    assert len(approved_reviews) == 1


def test_review_manager_list_reviews_by_outcome_enum(test_db_with_data):
    """Test filtering reviews by outcome using enum"""
    manager = ReviewManager(test_db_with_data)

    manager.create_review("code", "Review 1", "Desc 1")

    pending = manager.list_reviews(outcome=ReviewOutcome.PENDING)

    assert len(pending) == 1


def test_review_manager_get_pending_reviews(test_db_with_data):
    """Test getting pending reviews"""
    manager = ReviewManager(test_db_with_data)

    id1 = manager.create_review("code", "Review 1", "Desc 1")
    manager.create_review("code", "Review 2", "Desc 2")

    # Approve one
    manager.approve_review(id1, "Director")

    pending = manager.get_pending_reviews()

    assert len(pending) == 1
    assert pending[0].outcome == "pending"


def test_review_manager_approve_review(test_db_with_data):
    """Test approving a review"""
    manager = ReviewManager(test_db_with_data)

    review_id = manager.create_review("code", "Review", "Description")

    manager.approve_review(review_id, "Director", "Looks good")

    review = manager.get_review(review_id)
    assert review.outcome == "approved"
    assert review.reviewed_by == "Director"
    assert review.outcome_reason == "Looks good"
    assert review.reviewed_at is not None


def test_review_manager_approve_review_default_reviewer(test_db_with_data):
    """Test approving review with default reviewer"""
    manager = ReviewManager(test_db_with_data)

    review_id = manager.create_review("code", "Review", "Description")

    manager.approve_review(review_id)

    review = manager.get_review(review_id)
    assert review.reviewed_by == "Director"


def test_review_manager_reject_review(test_db_with_data):
    """Test rejecting a review"""
    manager = ReviewManager(test_db_with_data)

    review_id = manager.create_review("code", "Review", "Description")

    manager.reject_review(review_id, "Needs more work", "Director")

    review = manager.get_review(review_id)
    assert review.outcome == "rejected"
    assert review.reviewed_by == "Director"
    assert review.outcome_reason == "Needs more work"
    assert review.reviewed_at is not None


def test_review_manager_get_tasks_blocked_by_review_empty(test_db_with_data):
    """Test getting blocked tasks when none exist"""
    manager = ReviewManager(test_db_with_data)

    review_id = manager.create_review("code", "Review", "Description")

    blocked_tasks = manager.get_tasks_blocked_by_review(review_id)

    assert blocked_tasks == []


def test_review_manager_get_tasks_blocked_by_review(test_db_with_data):
    """Test getting tasks blocked by a review"""
    manager = ReviewManager(test_db_with_data)

    review_id = manager.create_review("code", "Review", "Description")

    # Create a block referencing this review
    test_db_with_data.execute_update(
        """
        INSERT INTO blocks (task_id, block_type, description)
        VALUES (:task_id, 'review', :description)
        """,
        {"task_id": "ENG-M-0001", "description": f"Waiting for review_id={review_id} approval"},
    )

    blocked_tasks = manager.get_tasks_blocked_by_review(review_id)

    assert blocked_tasks == ["ENG-M-0001"]
