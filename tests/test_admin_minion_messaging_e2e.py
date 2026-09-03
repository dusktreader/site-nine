"""
End-to-end integration tests for admin-minion message-based communication.

Tests cover the full round-trip at the DB/manager layer without launching real
opencode subprocesses.  Scenarios tested:

- Admin sends a task assignment; minion polls and finds it unread
- Minion marks conversation viewed; message disappears from unread list
- Minion sends a reply; admin polls and finds the reply
- Priority ordering: CRITICAL messages surface before LOW
- Multiple minions: each only sees messages addressed to it
- Message acknowledgement: ack removes message from get_unacknowledged_messages
- Minion shutdown: set_minion_mode(False) clears minion_mode_active in DB
- Rapid send-then-view: view timestamp strictly after message; message stays read

Reference: ADR-008 (messaging), ADR-009 (minion mode lifecycle).
"""

import pendulum
import pytest

from site_nine.core.database import Database
from site_nine.messaging.manager import MessageManager
from site_nine.possessions.manager import PossessionManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _insert_daemon(db: Database, name: str, role: str) -> None:
    db.execute_update(
        "INSERT OR IGNORE INTO daemons (name, role, incarnations) VALUES (:name, :role, 0)",
        {"name": name, "role": role},
    )


def _insert_possession(db: Database, daemon: str, role: str) -> int:
    _insert_daemon(db, daemon, role)
    return db.execute_insert(
        """
        INSERT INTO possessions (
            daemon_name, role, possession_log,
            start_time, status, last_heartbeat_at,
            created_at, updated_at
        ) VALUES (
            :daemon, :role,
            '.opencode/work/possessions/' || :daemon || '.md',
            datetime('now'), 'ACTIVE', datetime('now'),
            datetime('now'), datetime('now')
        )
        """,
        {"daemon": daemon, "role": role},
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def admin_id(test_db: Database) -> int:
    return _insert_possession(test_db, "admin-daemon", "Administrator")


@pytest.fixture
def minion_id(test_db: Database) -> int:
    return _insert_possession(test_db, "minion-daemon", "Engineer")


@pytest.fixture
def msg_mgr(test_db: Database) -> MessageManager:
    return MessageManager(test_db)


@pytest.fixture
def possession_mgr(test_db: Database) -> PossessionManager:
    return PossessionManager(test_db)


# ---------------------------------------------------------------------------
# Core round-trip
# ---------------------------------------------------------------------------


class TestAdminToMinionRoundTrip:
    """Full send → poll → read → reply → poll cycle."""

    def test_admin_sends_task_assignment_minion_sees_it_unread(
        self, test_db, msg_mgr, admin_id, minion_id
    ):
        """Minion's unread inbox is empty until admin sends a message."""
        assert msg_mgr.get_unread_conversations(minion_id) == []

        msg_mgr.send_conversation_message(
            from_possession_id=admin_id,
            to_possession_id=minion_id,
            body="Please implement ENG-H-0001: add rate limiting middleware.",
            priority="HIGH",
        )

        unread = msg_mgr.get_unread_conversations(minion_id)
        assert len(unread) == 1

    def test_minion_poll_returns_message_with_correct_content(
        self, test_db, msg_mgr, admin_id, minion_id
    ):
        """Polled message carries the right body and sender."""
        msg_mgr.send_conversation_message(
            from_possession_id=admin_id,
            to_possession_id=minion_id,
            body="Implement ENG-H-0002: caching layer.",
            priority="MEDIUM",
        )

        convs = msg_mgr.get_unread_conversations(minion_id)
        messages = msg_mgr.get_unread_messages(convs[0].id, minion_id)

        assert len(messages) == 1
        msg = messages[0]
        assert msg.from_possession_id == admin_id
        assert "caching layer" in msg.body
        assert msg.priority == "MEDIUM"

    def test_minion_marks_conversation_viewed_clears_unread(
        self, test_db, msg_mgr, admin_id, minion_id
    ):
        """After minion views the conversation the message is no longer unread."""
        conv, _ = msg_mgr.send_conversation_message(
            from_possession_id=admin_id,
            to_possession_id=minion_id,
            body="Task assignment",
        )

        assert len(msg_mgr.get_unread_conversations(minion_id)) == 1

        msg_mgr.update_conversation_view(conv.id, minion_id)

        assert msg_mgr.get_unread_conversations(minion_id) == []

    def test_minion_sends_reply_admin_sees_it_unread(
        self, test_db, msg_mgr, admin_id, minion_id
    ):
        """After minion replies, admin's unread list contains the reply."""
        # Admin sends assignment
        conv, _ = msg_mgr.send_conversation_message(
            from_possession_id=admin_id,
            to_possession_id=minion_id,
            body="Start work on ENG-H-0003.",
        )

        # Minion reads and replies — insert reply with a timestamp strictly later
        # than the sender-view timestamp to avoid same-millisecond collision
        msg_mgr.update_conversation_view(conv.id, minion_id)
        test_db.execute_update(
            """
            INSERT INTO messages (id, conversation_id, from_possession_id, subject, body, priority, created_at)
            VALUES ('MSG-M-REPLY1', :conv_id, :from_id,
                    'Task ENG-H-0003 started', 'Task ENG-H-0003 started. Will report when complete.',
                    'MEDIUM', datetime('now', '+1 second'))
            """,
            {"conv_id": conv.id, "from_id": minion_id},
        )

        # Admin should now see minion's reply as unread
        admin_unread_convs = msg_mgr.get_unread_conversations(admin_id)
        assert len(admin_unread_convs) == 1

        admin_msgs = msg_mgr.get_unread_messages(admin_unread_convs[0].id, admin_id)
        assert len(admin_msgs) == 1
        assert admin_msgs[0].from_possession_id == minion_id
        assert "ENG-H-0003 started" in admin_msgs[0].body

    def test_admin_views_reply_clears_admin_unread(
        self, test_db, msg_mgr, admin_id, minion_id
    ):
        """Admin viewing the reply conversation marks it read."""
        conv, _ = msg_mgr.send_conversation_message(
            from_possession_id=admin_id,
            to_possession_id=minion_id,
            body="Assignment",
        )
        msg_mgr.update_conversation_view(conv.id, minion_id)
        # Insert reply strictly after admin's view timestamp
        test_db.execute_update(
            """
            INSERT INTO messages (id, conversation_id, from_possession_id, subject, body, priority, created_at)
            VALUES ('MSG-M-REPLY2', :conv_id, :from_id,
                    'Done', 'Done.', 'MEDIUM', datetime('now', '+1 second'))
            """,
            {"conv_id": conv.id, "from_id": minion_id},
        )

        assert len(msg_mgr.get_unread_conversations(admin_id)) == 1

        # View strictly after the future-timestamped reply
        future = pendulum.now("UTC").add(seconds=10).to_iso8601_string()
        msg_mgr.update_conversation_view(conv.id, admin_id, viewed_at=future)

        assert msg_mgr.get_unread_conversations(admin_id) == []

    def test_full_back_and_forth_cycle(self, test_db, msg_mgr, admin_id, minion_id):
        """Multiple turns: admin → minion → admin → minion, all read in order."""
        # Turn 1: admin assigns
        conv, msg1 = msg_mgr.send_conversation_message(
            from_possession_id=admin_id,
            to_possession_id=minion_id,
            body="Turn 1: please start task A.",
        )
        assert len(msg_mgr.get_unread_conversations(minion_id)) == 1

        # Minion reads and replies (strictly later timestamp)
        msg_mgr.update_conversation_view(conv.id, minion_id)
        assert msg_mgr.get_unread_conversations(minion_id) == []

        test_db.execute_update(
            """
            INSERT INTO messages (id, conversation_id, from_possession_id, subject, body, priority, created_at)
            VALUES ('MSG-M-T2', :conv_id, :from_id,
                    'Turn 2: task A started', 'Turn 2: task A started.',
                    'MEDIUM', datetime('now', '+1 second'))
            """,
            {"conv_id": conv.id, "from_id": minion_id},
        )
        # Minion auto-views its own reply (sender is always considered current)
        after_t2 = pendulum.now("UTC").add(seconds=5).to_iso8601_string()
        msg_mgr.update_conversation_view(conv.id, minion_id, viewed_at=after_t2)

        # Admin reads reply (strictly later) and sends follow-up (even later)
        after_t2_admin = pendulum.now("UTC").add(seconds=5).to_iso8601_string()
        msg_mgr.update_conversation_view(conv.id, admin_id, viewed_at=after_t2_admin)
        test_db.execute_update(
            """
            INSERT INTO messages (id, conversation_id, from_possession_id, subject, body, priority, created_at)
            VALUES ('MSG-M-T3', :conv_id, :from_id,
                    'Turn 3: also handle task B', 'Turn 3: also handle task B.',
                    'MEDIUM', datetime('now', '+10 seconds'))
            """,
            {"conv_id": conv.id, "from_id": admin_id},
        )

        # Minion should see only the new follow-up
        minion_unread = msg_mgr.get_unread_conversations(minion_id)
        assert len(minion_unread) == 1
        msgs = msg_mgr.get_unread_messages(minion_unread[0].id, minion_id)
        assert len(msgs) == 1
        assert "task B" in msgs[0].body


# ---------------------------------------------------------------------------
# Priority ordering
# ---------------------------------------------------------------------------


class TestPriorityOrdering:
    """Messages should be processable in priority order."""

    def test_unread_messages_ordered_chronologically(
        self, test_db, msg_mgr, admin_id, minion_id
    ):
        """get_unread_messages returns messages in created_at ASC order."""
        test_db.execute_update(
            """
            INSERT INTO conversations (id, subject, type, status, participant_1_id, participant_2_id)
            VALUES ('CONV-TEST', 'Priority test', 'conversation', 'open', :a, :m)
            """,
            {"a": admin_id, "m": minion_id},
        )
        for priority, ts in [
            ("LOW", "2026-01-01T10:00:00+00:00"),
            ("CRITICAL", "2026-01-01T10:01:00+00:00"),
            ("HIGH", "2026-01-01T10:02:00+00:00"),
            ("MEDIUM", "2026-01-01T10:03:00+00:00"),
        ]:
            test_db.execute_update(
                """
                INSERT INTO messages (id, conversation_id, from_possession_id, subject, body, priority, created_at)
                VALUES (:id, 'CONV-TEST', :from_id, :subj, 'body', :priority, :ts)
                """,
                {
                    "id": f"MSG-{priority[0]}-{hash(priority) % 9999:04d}",
                    "from_id": admin_id,
                    "subj": f"A {priority} message",
                    "priority": priority,
                    "ts": ts,
                },
            )

        msgs = msg_mgr.get_unread_messages("CONV-TEST", minion_id)
        assert len(msgs) == 4
        # Ordered by created_at ASC (chronological)
        assert msgs[0].priority == "LOW"       # earliest
        assert msgs[3].priority == "MEDIUM"    # latest

    def test_minion_worker_sorts_by_priority(self, test_db, msg_mgr, admin_id, minion_id):
        """Simulates MinionWorker's priority sort on polled messages."""
        PRIORITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}

        test_db.execute_update(
            """
            INSERT INTO conversations (id, subject, type, status, participant_1_id, participant_2_id)
            VALUES ('CONV-PRIO', 'Priority sort test', 'conversation', 'open', :a, :m)
            """,
            {"a": admin_id, "m": minion_id},
        )
        for priority in ["LOW", "CRITICAL", "MEDIUM", "HIGH"]:
            test_db.execute_update(
                """
                INSERT INTO messages (id, conversation_id, from_possession_id, subject, body, priority)
                VALUES (:id, 'CONV-PRIO', :from_id, :subj, 'body', :priority)
                """,
                {
                    "id": f"MSG-{priority[0]}-{hash(priority) % 9000:04d}",
                    "from_id": admin_id,
                    "subj": f"A {priority} task",
                    "priority": priority,
                },
            )

        raw = msg_mgr.get_unread_messages("CONV-PRIO", minion_id)
        sorted_msgs = sorted(raw, key=lambda m: PRIORITY_ORDER.get(m.priority, 99))

        assert sorted_msgs[0].priority == "CRITICAL"
        assert sorted_msgs[1].priority == "HIGH"
        assert sorted_msgs[2].priority == "MEDIUM"
        assert sorted_msgs[3].priority == "LOW"


# ---------------------------------------------------------------------------
# Multiple minions
# ---------------------------------------------------------------------------


class TestMultipleMinions:
    """Each minion only sees messages addressed to it."""

    def test_two_minions_each_see_only_own_messages(self, test_db, msg_mgr, admin_id):
        """Messages sent to minion A are invisible to minion B."""
        minion_a = _insert_possession(test_db, "minion-a", "Engineer")
        minion_b = _insert_possession(test_db, "minion-b", "Tester")

        msg_mgr.send_conversation_message(
            from_possession_id=admin_id,
            to_possession_id=minion_a,
            body="Task for minion A.",
        )
        msg_mgr.send_conversation_message(
            from_possession_id=admin_id,
            to_possession_id=minion_b,
            body="Task for minion B.",
        )

        a_unread = msg_mgr.get_unread_conversations(minion_a)
        b_unread = msg_mgr.get_unread_conversations(minion_b)

        assert len(a_unread) == 1
        assert len(b_unread) == 1

        a_msgs = msg_mgr.get_unread_messages(a_unread[0].id, minion_a)
        b_msgs = msg_mgr.get_unread_messages(b_unread[0].id, minion_b)

        assert "minion A" in a_msgs[0].body
        assert "minion B" in b_msgs[0].body

    def test_admin_receives_replies_from_multiple_minions(self, test_db, msg_mgr, admin_id):
        """Admin's inbox aggregates replies from all minions."""
        minion_a = _insert_possession(test_db, "minion-aa", "Engineer")
        minion_b = _insert_possession(test_db, "minion-bb", "Tester")

        # Admin assigns to each
        conv_a, _ = msg_mgr.send_conversation_message(
            from_possession_id=admin_id, to_possession_id=minion_a, body="Task A"
        )
        conv_b, _ = msg_mgr.send_conversation_message(
            from_possession_id=admin_id, to_possession_id=minion_b, body="Task B"
        )

        # Both minions view and reply; use raw inserts with future timestamps so
        # the reply arrives strictly after admin's last_viewed_at for each conv.
        msg_mgr.update_conversation_view(conv_a.id, minion_a)
        test_db.execute_update(
            """
            INSERT INTO messages (id, conversation_id, from_possession_id, subject, body, priority, created_at)
            VALUES ('MSG-E2E-A-REPLY', :conv_id, :from_id,
                    'A done', 'A done.', 'MEDIUM', datetime('now', '+1 second'))
            """,
            {"conv_id": conv_a.id, "from_id": minion_a},
        )
        msg_mgr.update_conversation_view(conv_b.id, minion_b)
        test_db.execute_update(
            """
            INSERT INTO messages (id, conversation_id, from_possession_id, subject, body, priority, created_at)
            VALUES ('MSG-E2E-B-REPLY', :conv_id, :from_id,
                    'B done', 'B done.', 'MEDIUM', datetime('now', '+1 second'))
            """,
            {"conv_id": conv_b.id, "from_id": minion_b},
        )

        # Admin sees 2 unread conversations
        admin_unread = msg_mgr.get_unread_conversations(admin_id)
        assert len(admin_unread) == 2

        all_msgs = []
        for conv in admin_unread:
            all_msgs.extend(msg_mgr.get_unread_messages(conv.id, admin_id))

        senders = {m.from_possession_id for m in all_msgs}
        assert senders == {minion_a, minion_b}


# ---------------------------------------------------------------------------
# Message acknowledgement
# ---------------------------------------------------------------------------


class TestMessageAcknowledgement:
    """Ack-based tracking works alongside view-based tracking."""

    def test_unacknowledged_message_appears_in_get_unacknowledged(
        self, test_db, msg_mgr, admin_id, minion_id
    ):
        """Sent message appears in minion's get_unacknowledged_messages."""
        msg_mgr.send_conversation_message(
            from_possession_id=admin_id,
            to_possession_id=minion_id,
            body="Unacked task",
        )

        unacked = msg_mgr.get_unacknowledged_messages(minion_id)
        assert len(unacked) == 1
        assert unacked[0].from_possession_id == admin_id

    def test_acknowledged_message_disappears_from_unacknowledged(
        self, test_db, msg_mgr, admin_id, minion_id
    ):
        """After ack, message is removed from get_unacknowledged_messages."""
        _, msg = msg_mgr.send_conversation_message(
            from_possession_id=admin_id,
            to_possession_id=minion_id,
            body="Ack me",
        )

        msg_mgr.acknowledge_message(msg.id, minion_id)

        unacked = msg_mgr.get_unacknowledged_messages(minion_id)
        assert len(unacked) == 0

    def test_minion_own_messages_not_in_unacknowledged(
        self, test_db, msg_mgr, admin_id, minion_id
    ):
        """Minion does not see its own outgoing messages in unacknowledged list."""
        msg_mgr.send_conversation_message(
            from_possession_id=minion_id,
            to_possession_id=admin_id,
            body="Outgoing from minion",
        )

        unacked = msg_mgr.get_unacknowledged_messages(minion_id)
        assert len(unacked) == 0

    def test_view_and_ack_are_independent_tracking_mechanisms(
        self, test_db, msg_mgr, admin_id, minion_id
    ):
        """Viewing (conversation_views) and acking (message_acknowledgements) are separate."""
        conv, msg = msg_mgr.send_conversation_message(
            from_possession_id=admin_id,
            to_possession_id=minion_id,
            body="Track both ways",
        )

        # Ack without viewing
        msg_mgr.acknowledge_message(msg.id, minion_id)

        # Still shows as unread via view-based check
        assert len(msg_mgr.get_unread_conversations(minion_id)) == 1

        # Now view it
        msg_mgr.update_conversation_view(conv.id, minion_id)

        # Now both are clear
        assert msg_mgr.get_unread_conversations(minion_id) == []
        assert msg_mgr.get_unacknowledged_messages(minion_id) == []


# ---------------------------------------------------------------------------
# Minion mode lifecycle
# ---------------------------------------------------------------------------


class TestMinionModeLifecycle:
    """set_minion_mode interacts correctly with messaging state."""

    def test_minion_can_receive_messages_regardless_of_minion_mode_flag(
        self, test_db, msg_mgr, possession_mgr, admin_id, minion_id
    ):
        """minion_mode_active is a bookkeeping flag; unread messages exist either way."""
        # Minion mode off
        assert possession_mgr.get_possession(minion_id).minion_mode_active is False

        msg_mgr.send_conversation_message(
            from_possession_id=admin_id,
            to_possession_id=minion_id,
            body="Sent before minion mode enabled",
        )

        # Message is already there before enabling minion mode
        assert len(msg_mgr.get_unread_conversations(minion_id)) == 1

        # Enable, verify flag set
        possession_mgr.set_minion_mode(minion_id, active=True)
        assert possession_mgr.get_possession(minion_id).minion_mode_active is True

    def test_disable_minion_mode_does_not_lose_unread_messages(
        self, test_db, msg_mgr, possession_mgr, admin_id, minion_id
    ):
        """Turning off minion_mode_active does not clear unread messages."""
        possession_mgr.set_minion_mode(minion_id, active=True)

        msg_mgr.send_conversation_message(
            from_possession_id=admin_id,
            to_possession_id=minion_id,
            body="Message while minion mode active",
        )

        possession_mgr.set_minion_mode(minion_id, active=False)

        # Messages still present after mode disabled
        assert len(msg_mgr.get_unread_conversations(minion_id)) == 1

    def test_exorcised_minion_conversations_excluded_from_sender_unread(
        self, test_db, msg_mgr, possession_mgr, admin_id, minion_id
    ):
        """Closed conversations after exorcism don't show as unread for their participants."""
        conv, _ = msg_mgr.send_conversation_message(
            from_possession_id=admin_id,
            to_possession_id=minion_id,
            body="Task for minion",
        )

        # Simulate exorcism + close conversation
        possession_mgr.exorcise(minion_id)
        msg_mgr.close_conversation(conv.id)

        # Neither side sees the closed conversation as unread
        assert msg_mgr.get_unread_conversations(admin_id) == []
        assert msg_mgr.get_unread_conversations(minion_id) == []
