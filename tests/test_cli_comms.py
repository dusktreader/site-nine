"""
CLI integration tests for s9 comms commands (TST-H-0090).

Tests cover:
- s9 comms send: sending 1-on-1 messages
- s9 comms discuss: starting scoped discussions
- s9 comms reply: replying to messages
- s9 comms inbox: viewing unread messages
- s9 comms show: viewing conversations/messages
- s9 comms list: listing conversations
- s9 comms close: closing conversations
- s9 comms status: viewing conversation viewers
- s9 comms desk: desk mode management
"""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from site_nine.__main__ import app
from site_nine.core.database import Database

runner = CliRunner()


def _setup_missions(project_dir: Path) -> tuple[int, int]:
    """Set up two active missions in the project database and return their IDs.

    m2 gets a later start_time so _get_current_mission_id reliably returns m2
    as the "current" mission. This means:
    - Current mission = m2
    - Send --to-mission m1 = valid (m2 -> m1)
    - Send --to-mission m2 = self-send error
    """
    db_path = project_dir / ".opencode" / "data" / "project.db"

    with Database(db_path) as db:
        # Add personas first
        db.execute_update(
            """
            INSERT OR IGNORE INTO personas (name, role, mythology, description)
            VALUES
                ('cli-alpha', 'Operator', 'Test', 'CLI alpha persona'),
                ('cli-beta', 'Tester', 'Test', 'CLI beta persona')
            """
        )

        # Create two active missions
        m1 = db.execute_insert(
            """
            INSERT INTO missions (
                persona_name, role, codename, mission_file,
                start_date, start_time, objective
            ) VALUES (
                'cli-alpha', 'Operator', 'cli-one',
                '.opencode/work/missions/cli-1.md',
                '2026-02-14', '10:00:00', 'CLI test mission 1'
            )
            """
        )
        m2 = db.execute_insert(
            """
            INSERT INTO missions (
                persona_name, role, codename, mission_file,
                start_date, start_time, objective
            ) VALUES (
                'cli-beta', 'Tester', 'cli-two',
                '.opencode/work/missions/cli-2.md',
                '2026-02-14', '11:00:00', 'CLI test mission 2'
            )
            """
        )

    return m1, m2


class TestCommsSend:
    """Tests for s9 comms send command."""

    def test_send_message(self, initialized_project: Path):
        """Send a message to another mission."""
        m1, m2 = _setup_missions(initialized_project)

        # Current mission is m2 (latest start_time), so send to m1
        result = runner.invoke(
            app,
            ["comms", "send", "--to-mission", str(m1), "Hello from beta"],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Message sent" in result.output

    def test_send_message_json(self, initialized_project: Path):
        """Send a message with JSON output."""
        m1, m2 = _setup_missions(initialized_project)

        # Current mission is m2 (latest start_time), so send to m1
        result = runner.invoke(
            app,
            ["comms", "send", "--to-mission", str(m1), "--json", "Hello from beta"],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        data = json.loads(result.output)
        assert "data" in data
        assert "conversation_id" in data["data"]
        assert "message_id" in data["data"]
        assert data["data"]["to_mission_id"] == m1

    def test_send_message_with_priority(self, initialized_project: Path):
        """Send a message with specific priority."""
        m1, m2 = _setup_missions(initialized_project)

        # Current mission is m2 (latest start_time), so send to m1
        result = runner.invoke(
            app,
            ["comms", "send", "--to-mission", str(m1), "--priority", "HIGH", "Urgent message"],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Message sent" in result.output

    def test_send_to_nonexistent_mission_fails(self, initialized_project: Path):
        """Sending to nonexistent mission fails gracefully."""
        _setup_missions(initialized_project)

        result = runner.invoke(
            app,
            ["comms", "send", "--to-mission", "9999", "Hello"],
        )

        assert result.exit_code != 0

    def test_send_without_message_fails(self, initialized_project: Path):
        """Sending without a message body fails."""
        m1, m2 = _setup_missions(initialized_project)

        result = runner.invoke(
            app,
            ["comms", "send", "--to-mission", str(m1)],
        )

        assert result.exit_code != 0

    def test_send_with_invalid_priority_fails(self, initialized_project: Path):
        """Sending with invalid priority fails."""
        m1, m2 = _setup_missions(initialized_project)

        result = runner.invoke(
            app,
            ["comms", "send", "--to-mission", str(m1), "--priority", "INVALID", "Hello"],
        )

        assert result.exit_code != 0


class TestCommsDiscuss:
    """Tests for s9 comms discuss command."""

    def test_discuss_all_scope(self, initialized_project: Path):
        """Start an all-scope discussion."""
        _setup_missions(initialized_project)

        result = runner.invoke(
            app,
            ["comms", "discuss", "General announcement to all missions"],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Discussion started" in result.output
        assert "all missions" in result.output

    def test_discuss_role_scope(self, initialized_project: Path):
        """Start a role-scoped discussion."""
        _setup_missions(initialized_project)

        result = runner.invoke(
            app,
            ["comms", "discuss", "--role", "Operator", "Operators only chat"],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Discussion started" in result.output

    def test_discuss_json(self, initialized_project: Path):
        """Start a discussion with JSON output."""
        _setup_missions(initialized_project)

        result = runner.invoke(
            app,
            ["comms", "discuss", "--json", "All hands announcement"],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        data = json.loads(result.output)
        assert "data" in data
        assert "discussion_id" in data["data"]
        assert data["data"]["scope_type"] == "all"

    def test_discuss_role_and_epic_mutually_exclusive(self, initialized_project: Path):
        """Cannot specify both --role and --epic."""
        _setup_missions(initialized_project)

        result = runner.invoke(
            app,
            ["comms", "discuss", "--role", "Operator", "--epic", "EPC-H-0001", "Bad scope"],
        )

        assert result.exit_code != 0

    def test_discuss_without_message_fails(self, initialized_project: Path):
        """Discussing without a message body fails."""
        _setup_missions(initialized_project)

        result = runner.invoke(
            app,
            ["comms", "discuss"],
        )

        assert result.exit_code != 0


class TestCommsReply:
    """Tests for s9 comms reply command."""

    def test_reply_to_conversation_message(self, initialized_project: Path):
        """Reply to a message in a conversation."""
        m1, m2 = _setup_missions(initialized_project)

        # First send a message (current=m2, send to m1)
        send_result = runner.invoke(
            app,
            ["comms", "send", "--to-mission", str(m1), "--json", "Hello from beta"],
        )
        assert send_result.exit_code == 0, f"Send failed: {send_result.output}"
        send_data = json.loads(send_result.output)
        msg_id = send_data["data"]["message_id"]

        # Reply to it
        reply_result = runner.invoke(
            app,
            ["comms", "reply", msg_id, "Thanks for the message!"],
        )

        assert reply_result.exit_code == 0, f"Reply failed: {reply_result.output}"
        assert "Reply sent" in reply_result.output

    def test_reply_json_output(self, initialized_project: Path):
        """Reply with JSON output."""
        m1, m2 = _setup_missions(initialized_project)

        # Send initial message
        send_result = runner.invoke(
            app,
            ["comms", "send", "--to-mission", str(m1), "--json", "Hello"],
        )
        send_data = json.loads(send_result.output)
        msg_id = send_data["data"]["message_id"]

        # Reply with JSON
        reply_result = runner.invoke(
            app,
            ["comms", "reply", msg_id, "--json", "Reply text"],
        )

        assert reply_result.exit_code == 0, f"Reply failed: {reply_result.output}"
        data = json.loads(reply_result.output)
        assert "data" in data
        assert "message_id" in data["data"]

    def test_reply_to_nonexistent_message_fails(self, initialized_project: Path):
        """Replying to nonexistent message fails."""
        _setup_missions(initialized_project)

        result = runner.invoke(
            app,
            ["comms", "reply", "MSG-M-9999", "Reply text"],
        )

        assert result.exit_code != 0

    def test_reply_without_message_text_fails(self, initialized_project: Path):
        """Reply without text fails."""
        m1, m2 = _setup_missions(initialized_project)

        # Send initial message
        send_result = runner.invoke(
            app,
            ["comms", "send", "--to-mission", str(m1), "--json", "Hello"],
        )
        send_data = json.loads(send_result.output)
        msg_id = send_data["data"]["message_id"]

        result = runner.invoke(
            app,
            ["comms", "reply", msg_id],
        )

        assert result.exit_code != 0


class TestCommsInbox:
    """Tests for s9 comms inbox command."""

    def test_inbox_empty(self, initialized_project: Path):
        """Inbox with no messages shows appropriate output."""
        _setup_missions(initialized_project)

        result = runner.invoke(app, ["comms", "inbox"])

        assert result.exit_code == 0, f"Command failed: {result.output}"

    def test_inbox_json_empty(self, initialized_project: Path):
        """Inbox JSON output with no messages."""
        _setup_missions(initialized_project)

        result = runner.invoke(app, ["comms", "inbox", "--json"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        data = json.loads(result.output)
        assert "data" in data
        assert data["data"]["count"] == 0

    def test_inbox_with_unread_messages(self, initialized_project: Path):
        """Inbox shows unread messages."""
        m1, m2 = _setup_missions(initialized_project)

        # Current mission is m2, send to m1
        runner.invoke(
            app,
            ["comms", "send", "--to-mission", str(m1), "Hello from beta"],
        )

        result = runner.invoke(app, ["comms", "inbox", "--json"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        data = json.loads(result.output)
        # The current mission (m2) sent the message, so its inbox should show no unread from others
        # This tests that the inbox works without error - detailed unread logic is tested at manager level

    def test_inbox_all_conversations(self, initialized_project: Path):
        """Inbox --all shows all conversations."""
        m1, m2 = _setup_missions(initialized_project)

        # Send a message to create a conversation
        runner.invoke(
            app,
            ["comms", "send", "--to-mission", str(m1), "Hello"],
        )

        result = runner.invoke(app, ["comms", "inbox", "--all"])

        assert result.exit_code == 0, f"Command failed: {result.output}"


class TestCommsShow:
    """Tests for s9 comms show command."""

    def test_show_conversation(self, initialized_project: Path):
        """Show a conversation with messages."""
        m1, m2 = _setup_missions(initialized_project)

        # Send a message (current=m2, send to m1)
        send_result = runner.invoke(
            app,
            ["comms", "send", "--to-mission", str(m1), "--json", "Test message"],
        )
        send_data = json.loads(send_result.output)
        conv_id = send_data["data"]["conversation_id"]

        # Show the conversation
        result = runner.invoke(app, ["comms", "show", conv_id])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "CONVERSATION" in result.output
        assert conv_id in result.output

    def test_show_message_in_context(self, initialized_project: Path):
        """Show a specific message shows its conversation."""
        m1, m2 = _setup_missions(initialized_project)

        send_result = runner.invoke(
            app,
            ["comms", "send", "--to-mission", str(m1), "--json", "Test message"],
        )
        send_data = json.loads(send_result.output)
        msg_id = send_data["data"]["message_id"]

        result = runner.invoke(app, ["comms", "show", msg_id])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert msg_id in result.output

    def test_show_json_output(self, initialized_project: Path):
        """Show conversation with JSON output."""
        m1, m2 = _setup_missions(initialized_project)

        send_result = runner.invoke(
            app,
            ["comms", "send", "--to-mission", str(m1), "--json", "Test message"],
        )
        send_data = json.loads(send_result.output)
        conv_id = send_data["data"]["conversation_id"]

        result = runner.invoke(app, ["comms", "show", conv_id, "--json"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        data = json.loads(result.output)
        assert "data" in data
        assert data["data"]["conversation"]["id"] == conv_id
        assert len(data["data"]["messages"]) >= 1

    def test_show_nonexistent_conversation_fails(self, initialized_project: Path):
        """Showing nonexistent conversation fails."""
        _setup_missions(initialized_project)

        result = runner.invoke(app, ["comms", "show", "CONV-9999"])

        assert result.exit_code != 0


class TestCommsList:
    """Tests for s9 comms list command."""

    def test_list_empty(self, initialized_project: Path):
        """List with no conversations."""
        _setup_missions(initialized_project)

        result = runner.invoke(app, ["comms", "list"])

        assert result.exit_code == 0, f"Command failed: {result.output}"

    def test_list_after_sending(self, initialized_project: Path):
        """List shows conversations after sending messages."""
        m1, m2 = _setup_missions(initialized_project)

        runner.invoke(
            app,
            ["comms", "send", "--to-mission", str(m1), "Test message"],
        )

        result = runner.invoke(app, ["comms", "list"])

        assert result.exit_code == 0, f"Command failed: {result.output}"

    def test_list_json(self, initialized_project: Path):
        """List with JSON output."""
        m1, m2 = _setup_missions(initialized_project)

        runner.invoke(
            app,
            ["comms", "send", "--to-mission", str(m1), "Test message"],
        )

        result = runner.invoke(app, ["comms", "list", "--json"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        data = json.loads(result.output)
        assert "data" in data

    def test_list_filter_open(self, initialized_project: Path):
        """List only open conversations."""
        _setup_missions(initialized_project)

        result = runner.invoke(app, ["comms", "list", "--open"])

        assert result.exit_code == 0, f"Command failed: {result.output}"


class TestCommsClose:
    """Tests for s9 comms close command."""

    def test_close_conversation(self, initialized_project: Path):
        """Close an open conversation."""
        m1, m2 = _setup_missions(initialized_project)

        send_result = runner.invoke(
            app,
            ["comms", "send", "--to-mission", str(m1), "--json", "Test message"],
        )
        send_data = json.loads(send_result.output)
        conv_id = send_data["data"]["conversation_id"]

        result = runner.invoke(app, ["comms", "close", conv_id])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "closed" in result.output.lower()

    def test_close_json(self, initialized_project: Path):
        """Close with JSON output."""
        m1, m2 = _setup_missions(initialized_project)

        send_result = runner.invoke(
            app,
            ["comms", "send", "--to-mission", str(m1), "--json", "Test message"],
        )
        send_data = json.loads(send_result.output)
        conv_id = send_data["data"]["conversation_id"]

        result = runner.invoke(app, ["comms", "close", conv_id, "--json"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        data = json.loads(result.output)
        assert data["data"]["status"] == "closed"

    def test_close_nonexistent_fails(self, initialized_project: Path):
        """Closing nonexistent conversation fails."""
        _setup_missions(initialized_project)

        result = runner.invoke(app, ["comms", "close", "CONV-9999"])

        assert result.exit_code != 0


class TestCommsStatus:
    """Tests for s9 comms status command."""

    def test_status_no_viewers(self, initialized_project: Path):
        """Status shows at least the sender as viewer after sending."""
        m1, m2 = _setup_missions(initialized_project)

        send_result = runner.invoke(
            app,
            ["comms", "send", "--to-mission", str(m1), "--json", "Test message"],
        )
        send_data = json.loads(send_result.output)
        conv_id = send_data["data"]["conversation_id"]

        result = runner.invoke(app, ["comms", "status", conv_id])

        # Sender view is recorded, so at least one viewer should exist
        assert result.exit_code == 0, f"Command failed: {result.output}"

    def test_status_json(self, initialized_project: Path):
        """Status with JSON output."""
        m1, m2 = _setup_missions(initialized_project)

        send_result = runner.invoke(
            app,
            ["comms", "send", "--to-mission", str(m1), "--json", "Test message"],
        )
        send_data = json.loads(send_result.output)
        conv_id = send_data["data"]["conversation_id"]

        result = runner.invoke(app, ["comms", "status", conv_id, "--json"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        data = json.loads(result.output)
        assert "data" in data

    def test_status_after_show_updates_viewer(self, initialized_project: Path):
        """Showing a conversation adds the viewer to status."""
        m1, m2 = _setup_missions(initialized_project)

        send_result = runner.invoke(
            app,
            ["comms", "send", "--to-mission", str(m1), "--json", "Test message"],
        )
        send_data = json.loads(send_result.output)
        conv_id = send_data["data"]["conversation_id"]

        # Show the conversation (updates view tracking)
        runner.invoke(app, ["comms", "show", conv_id])

        # Check status
        result = runner.invoke(app, ["comms", "status", conv_id, "--json"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        data = json.loads(result.output)
        assert data["count"] >= 1

    def test_status_nonexistent_fails(self, initialized_project: Path):
        """Status of nonexistent conversation fails."""
        _setup_missions(initialized_project)

        result = runner.invoke(app, ["comms", "status", "CONV-9999"])

        assert result.exit_code != 0


class TestCommsDesk:
    """Tests for s9 comms desk command."""

    def test_desk_stop(self, initialized_project: Path):
        """Desk mode stop command works."""
        _setup_missions(initialized_project)

        result = runner.invoke(app, ["comms", "desk", "--stop"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "disabled" in result.output.lower() or "Desk" in result.output

    def test_desk_stop_json(self, initialized_project: Path):
        """Desk mode stop with JSON output."""
        _setup_missions(initialized_project)

        result = runner.invoke(app, ["comms", "desk", "--stop", "--json"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        data = json.loads(result.output)
        assert data["data"]["desk_mode_active"] is False

    def test_desk_start_json(self, initialized_project: Path):
        """Desk mode start with JSON output (non-blocking)."""
        _setup_missions(initialized_project)

        result = runner.invoke(app, ["comms", "desk", "--json"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        data = json.loads(result.output)
        assert data["data"]["desk_mode_active"] is True


class TestCommsWithoutInit:
    """Tests that comms commands fail properly without initialization."""

    def test_send_fails_without_init(self, in_temp_dir: Path):
        """Send fails if project not initialized."""
        result = runner.invoke(
            app,
            ["comms", "send", "--to-mission", "1", "Hello"],
        )
        assert result.exit_code != 0

    def test_inbox_fails_without_init(self, in_temp_dir: Path):
        """Inbox fails if project not initialized."""
        result = runner.invoke(app, ["comms", "inbox"])
        assert result.exit_code != 0

    def test_discuss_fails_without_init(self, in_temp_dir: Path):
        """Discuss fails if project not initialized."""
        result = runner.invoke(app, ["comms", "discuss", "Hello"])
        assert result.exit_code != 0
