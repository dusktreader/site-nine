"""Tests for blocks manager"""

import pytest
from site_nine.blocks.manager import BlockManager
from site_nine.core.database import Database


def test_block_manager_create_block(test_db_with_data):
    """Test creating a block"""
    manager = BlockManager(test_db_with_data)

    block_id = manager.create_block(
        task_id="ENG-M-0001", block_type="external-dependency", description="Waiting for API key from vendor"
    )

    assert block_id > 0

    # Verify block was created
    block = manager.get_block(block_id)
    assert block is not None
    assert block.task_id == "ENG-M-0001"
    assert block.block_type == "external-dependency"
    assert block.description == "Waiting for API key from vendor"
    assert block.resolved_at is None


def test_block_manager_get_block_not_found(test_db_with_data):
    """Test getting non-existent block returns None"""
    manager = BlockManager(test_db_with_data)

    block = manager.get_block(999)

    assert block is None


def test_block_manager_list_blocks_empty(test_db_with_data):
    """Test listing blocks when none exist"""
    manager = BlockManager(test_db_with_data)

    blocks = manager.list_blocks()

    assert blocks == []


def test_block_manager_list_blocks(test_db_with_data):
    """Test listing all blocks"""
    manager = BlockManager(test_db_with_data)

    id1 = manager.create_block("ENG-M-0001", "external-dependency", "Block 1")
    id2 = manager.create_block("ENG-M-0002", "waiting-for-access", "Block 2")

    blocks = manager.list_blocks()

    assert len(blocks) == 2
    block_ids = {b.id for b in blocks}
    assert block_ids == {id1, id2}


def test_block_manager_list_blocks_by_task(test_db_with_data):
    """Test filtering blocks by task ID"""
    manager = BlockManager(test_db_with_data)

    manager.create_block("ENG-M-0001", "external-dependency", "Block 1")
    manager.create_block("ENG-M-0002", "waiting-for-access", "Block 2")
    manager.create_block("ENG-M-0001", "review", "Block 3")

    task1_blocks = manager.list_blocks(task_id="ENG-M-0001")

    assert len(task1_blocks) == 2
    assert all(b.task_id == "ENG-M-0001" for b in task1_blocks)


def test_block_manager_list_blocks_resolved(test_db_with_data):
    """Test filtering blocks by resolution status"""
    manager = BlockManager(test_db_with_data)

    id1 = manager.create_block("ENG-M-0001", "external-dependency", "Block 1")
    manager.create_block("ENG-M-0001", "waiting-for-access", "Block 2")

    # Resolve one block
    manager.resolve_block(id1)

    resolved_blocks = manager.list_blocks(resolved=True)
    unresolved_blocks = manager.list_blocks(resolved=False)

    assert len(resolved_blocks) == 1
    assert len(unresolved_blocks) == 1
    assert resolved_blocks[0].id == id1


def test_block_manager_get_unresolved_blocks(test_db_with_data):
    """Test getting unresolved blocks"""
    manager = BlockManager(test_db_with_data)

    id1 = manager.create_block("ENG-M-0001", "external-dependency", "Block 1")
    manager.create_block("ENG-M-0001", "waiting-for-access", "Block 2")

    # Resolve one
    manager.resolve_block(id1)

    unresolved = manager.get_unresolved_blocks()

    assert len(unresolved) == 1
    assert unresolved[0].resolved_at is None


def test_block_manager_get_unresolved_blocks_for_task(test_db_with_data):
    """Test getting unresolved blocks for specific task"""
    manager = BlockManager(test_db_with_data)

    manager.create_block("ENG-M-0001", "external-dependency", "Block 1")
    manager.create_block("ENG-M-0002", "waiting-for-access", "Block 2")

    task1_unresolved = manager.get_unresolved_blocks(task_id="ENG-M-0001")

    assert len(task1_unresolved) == 1
    assert task1_unresolved[0].task_id == "ENG-M-0001"


def test_block_manager_resolve_block(test_db_with_data):
    """Test resolving a block"""
    manager = BlockManager(test_db_with_data)

    block_id = manager.create_block("ENG-M-0001", "external-dependency", "Block 1")

    manager.resolve_block(block_id)

    block = manager.get_block(block_id)
    assert block.resolved_at is not None


def test_block_manager_delete_block(test_db_with_data):
    """Test deleting a block"""
    manager = BlockManager(test_db_with_data)

    block_id = manager.create_block("ENG-M-0001", "external-dependency", "Block 1")

    manager.delete_block(block_id)

    block = manager.get_block(block_id)
    assert block is None


def test_block_manager_check_task_blocked(test_db_with_data):
    """Test checking if task is blocked"""
    manager = BlockManager(test_db_with_data)

    # Task with no blocks
    blocks = manager.check_task_blocked("ENG-M-0001")
    assert blocks == []

    # Add a block
    manager.create_block("ENG-M-0001", "external-dependency", "Block 1")

    blocks = manager.check_task_blocked("ENG-M-0001")
    assert len(blocks) == 1


def test_block_manager_check_task_blocked_ignores_resolved(test_db_with_data):
    """Test check_task_blocked only returns unresolved blocks"""
    manager = BlockManager(test_db_with_data)

    id1 = manager.create_block("ENG-M-0001", "external-dependency", "Block 1")
    manager.create_block("ENG-M-0001", "waiting-for-access", "Block 2")

    # Resolve one
    manager.resolve_block(id1)

    blocks = manager.check_task_blocked("ENG-M-0001")
    assert len(blocks) == 1
    assert blocks[0].id != id1
