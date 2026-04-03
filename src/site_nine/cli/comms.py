from __future__ import annotations

import sys
from typing import Annotated

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table
from snick import conjoin
from typerdrive import handle_errors, terminal_message

from site_nine.cli.json_utils import format_json_error, format_json_response, output_json
from site_nine.cli.utils import CLIError, require_db_path
from site_nine.core.database import Database
from site_nine.exceptions import SiteNineError
from site_nine.messaging import Message, MessageManager
from site_nine.possessions import PossessionManager

app = typer.Typer(help="Agent-to-agent messaging and coordination")
console = Console()


def _get_current_mission_id(db: Database) -> int:
    """Get the current active possession ID from the session."""
    # For now, get the most recent active possession
    # TODO: In future, this should come from the OpenCode session context
    rows = db.execute_query(
        """
        SELECT id FROM possessions
        WHERE status != 'EXORCISED'
        ORDER BY start_time DESC, id DESC
        LIMIT 1
        """
    )
    CLIError.require_condition(
        bool(rows),
        "No active mission found. Start a mission first with: s9 mission start",
    )
    return rows[0]["id"]


def _format_desk_inbox_summary(
    msg_manager: MessageManager,
    conversations: list,
    possession_id: int,
) -> list[str]:
    """Format unread messages as inbox-style summary lines for desk mode display.

    Collects unread messages from other possessions across all conversations and formats
    them per ADR-009 lines 160-171 specification.

    Args:
        msg_manager: MessageManager instance for querying unread messages
        conversations: List of unread Conversation objects
        possession_id: Current possession ID (to exclude own messages)

    Returns:
        List of formatted output lines. Empty list if no unread messages from others.
    """
    inbox_messages: list[Message] = []
    for conv in conversations:
        unread_msgs = msg_manager.get_unread_messages(conv.id, possession_id)
        for msg in unread_msgs:
            if msg.from_possession_id != possession_id:
                inbox_messages.append(msg)

    if not inbox_messages:
        return []

    lines: list[str] = []
    lines.append(f"Checking comms... {len(inbox_messages)} new message(s)!")
    for msg in inbox_messages:
        lines.append(f'- {msg.id} from Mission #{msg.from_possession_id}: "{msg.subject}"')
    lines.append("")
    lines.append('Reply with: s9 comms reply <MSG_ID> "your response"')
    return lines


def _format_message_preview(body: str, max_length: int = 60) -> str:
    """Format message body as a preview."""
    # Remove markdown formatting for preview
    preview = body.replace("#", "").replace("*", "").replace("_", "").strip()
    # Take first line
    preview = preview.split("\n")[0]
    if len(preview) > max_length:
        preview = preview[: max_length - 3] + "..."
    return preview


@app.command()
@handle_errors("Failed to send message", handle_exc_class=SiteNineError)
def send(
    to_mission: Annotated[int, typer.Option("--to-mission", "-m", help="Recipient mission ID")],
    message: Annotated[str | None, typer.Argument(help="Message text")] = None,
    priority: Annotated[str, typer.Option("--priority", "-p", help="Message priority")] = "MEDIUM",
    task_id: Annotated[str | None, typer.Option("--task", "-t", help="Related task ID")] = None,
    epic_id: Annotated[str | None, typer.Option("--epic", "-e", help="Related epic ID")] = None,
    artifact_path: Annotated[str | None, typer.Option("--artifact", "-a", help="Related file/artifact")] = None,
    body_from_stdin: Annotated[bool, typer.Option("--body-from-stdin", help="Read message from stdin")] = False,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")] = False,
) -> None:
    """Send a 1-on-1 message to another mission.

    Auto-creates conversation on first message between two missions.
    Reuses open conversations; creates new conversation if previous was closed.
    """
    db_path = require_db_path()

    # Validate priority
    valid_priorities = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    priority = priority.upper()
    CLIError.require_condition(
        priority in valid_priorities,
        f"Invalid priority: {priority}. Valid values: {', '.join(valid_priorities)}",
    )

    # Get message body
    body = ""
    if body_from_stdin:
        body = sys.stdin.read().strip()
        CLIError.require_condition(bool(body), "Message body from stdin is empty")
    elif message:
        body = message
    else:
        CLIError.require_condition(False, "Provide message as argument or use --body-from-stdin")

    with Database(db_path) as db:
        from_mission_id = _get_current_mission_id(db)

        # Validate recipient exists
        possession_manager = PossessionManager(db)
        to_mission_obj = possession_manager.get_possession(to_mission)
        CLIError.require_condition(
            to_mission_obj is not None,
            f"Mission {to_mission} not found. Use 's9 mission list' to see available missions.",
        )

        msg_manager = MessageManager(db)
        conversation, msg = msg_manager.send_conversation_message(
            from_possession_id=from_mission_id,
            to_possession_id=to_mission,
            body=body,
            priority=priority,
            task_id=task_id,
            epic_id=epic_id,
            artifact_path=artifact_path,
        )

    if json_output:
        output_json(
            format_json_response(
                {
                    "conversation_id": conversation.id,
                    "message_id": msg.id,
                    "from_mission_id": from_mission_id,
                    "to_mission_id": to_mission,
                    "subject": msg.subject,
                    "priority": msg.priority,
                }
            )
        )
    else:
        terminal_message(
            conjoin(
                f"Message sent to mission {to_mission}",
                f"  Conversation: {conversation.id}",
                f"  Message: {msg.id}",
                f"  Priority: {msg.priority}",
            ),
            subject="Done",
            subject_color="green",
        )


@app.command()
@handle_errors("Failed to start discussion", handle_exc_class=SiteNineError)
def discuss(
    message: Annotated[str | None, typer.Argument(help="Message text")] = None,
    role: Annotated[str | None, typer.Option("--role", "-r", help="Role-scoped discussion")] = None,
    epic: Annotated[str | None, typer.Option("--epic", "-e", help="Epic-scoped discussion")] = None,
    priority: Annotated[str, typer.Option("--priority", "-p", help="Message priority")] = "MEDIUM",
    task_id: Annotated[str | None, typer.Option("--task", "-t", help="Related task ID")] = None,
    body_from_stdin: Annotated[bool, typer.Option("--body-from-stdin", help="Read message from stdin")] = False,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")] = False,
) -> None:
    """Start a scoped group discussion.

    Scope options:
    - --role: Discussion visible to all missions with that role
    - --epic: Discussion visible to all missions working on that epic
    - Neither: Discussion visible to all active missions (broadcast)
    """
    db_path = require_db_path()

    # Validate scope options are mutually exclusive
    CLIError.require_condition(
        not (role and epic),
        "Cannot specify both --role and --epic. Choose one scope type.",
    )

    # Validate priority
    valid_priorities = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    priority = priority.upper()
    CLIError.require_condition(
        priority in valid_priorities,
        f"Invalid priority: {priority}. Valid values: {', '.join(valid_priorities)}",
    )

    # Get message body
    body = ""
    if body_from_stdin:
        body = sys.stdin.read().strip()
        CLIError.require_condition(bool(body), "Message body from stdin is empty")
    elif message:
        body = message
    else:
        CLIError.require_condition(False, "Provide message as argument or use --body-from-stdin")

    # Determine scope
    if role:
        scope_type = "role"
        scope_role = role.title()
        scope_epic_id = None
    elif epic:
        scope_type = "epic"
        scope_role = None
        scope_epic_id = epic
    else:
        scope_type = "all"
        scope_role = None
        scope_epic_id = None

    with Database(db_path) as db:
        from_mission_id = _get_current_mission_id(db)

        msg_manager = MessageManager(db)

        # Extract subject from body
        subject = msg_manager._extract_subject_from_text(body)

        # Create discussion
        discussion = msg_manager.create_discussion(
            subject=subject,
            scope_type=scope_type,
            scope_role=scope_role,
            scope_epic_id=scope_epic_id,
            task_id=task_id,
            epic_id=epic,
        )

        # Send first message
        msg = msg_manager.create_message(
            conversation_id=discussion.id,
            from_possession_id=from_mission_id,
            subject=subject,
            body=body,
            priority=priority,
            parent_message_id=None,  # Root message
            task_id=task_id,
            epic_id=epic,
        )

        # Update view for sender
        msg_manager.update_conversation_view(discussion.id, from_mission_id)

    if json_output:
        output_json(
            format_json_response(
                {
                    "discussion_id": discussion.id,
                    "message_id": msg.id,
                    "scope_type": scope_type,
                    "scope_role": scope_role,
                    "scope_epic_id": scope_epic_id,
                    "subject": subject,
                    "priority": msg.priority,
                }
            )
        )
    else:
        scope_desc = (
            f"role={scope_role}" if scope_role else f"epic={scope_epic_id}" if scope_epic_id else "all missions"
        )
        terminal_message(
            conjoin(
                f"Discussion started ({scope_desc})",
                f"  Discussion: {discussion.id}",
                f"  Message: {msg.id}",
                f"  Subject: {subject}",
                f"  Priority: {msg.priority}",
            ),
            subject="Done",
            subject_color="green",
        )


@app.command()
@handle_errors("Failed to reply to message", handle_exc_class=SiteNineError)
def reply(
    message_id: Annotated[str, typer.Argument(help="Message ID to reply to")],
    message: Annotated[str | None, typer.Argument(help="Reply text")] = None,
    priority: Annotated[str, typer.Option("--priority", "-p", help="Message priority")] = "MEDIUM",
    body_from_stdin: Annotated[bool, typer.Option("--body-from-stdin", help="Read message from stdin")] = False,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")] = False,
) -> None:
    """Reply to a message in a conversation or discussion.

    For conversations: Reply is flat (no threading).
    For discussions: Reply creates threaded message.
    """
    db_path = require_db_path()

    # Validate priority
    valid_priorities = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    priority = priority.upper()
    CLIError.require_condition(
        priority in valid_priorities,
        f"Invalid priority: {priority}. Valid values: {', '.join(valid_priorities)}",
    )

    # Get message body
    body = ""
    if body_from_stdin:
        body = sys.stdin.read().strip()
        CLIError.require_condition(bool(body), "Message body from stdin is empty")
    elif message:
        body = message
    else:
        CLIError.require_condition(False, "Provide message as argument or use --body-from-stdin")

    with Database(db_path) as db:
        from_mission_id = _get_current_mission_id(db)
        msg_manager = MessageManager(db)

        # Get parent message
        parent = msg_manager.get_message(message_id)
        CLIError.require_condition(parent is not None, f"Message {message_id} not found")
        assert parent is not None

        # Get conversation
        conversation = msg_manager.get_conversation(parent.conversation_id)
        CLIError.require_condition(conversation is not None, f"Conversation {parent.conversation_id} not found")
        assert conversation is not None

        # Extract subject
        subject = msg_manager._extract_subject_from_text(body)

        # For conversations, don't thread (parent_message_id=None)
        # For discussions, thread (parent_message_id=message_id)
        parent_msg_id = None if conversation.is_conversation() else message_id

        # Create reply
        reply_msg = msg_manager.create_message(
            conversation_id=conversation.id,
            from_possession_id=from_mission_id,
            subject=subject,
            body=body,
            priority=priority,
            parent_message_id=parent_msg_id,
            task_id=parent.task_id,
            epic_id=parent.epic_id,
        )

        # Update view for sender
        msg_manager.update_conversation_view(conversation.id, from_mission_id)

    if json_output:
        output_json(
            format_json_response(
                {
                    "message_id": reply_msg.id,
                    "conversation_id": conversation.id,
                    "parent_message_id": message_id,
                    "priority": reply_msg.priority,
                }
            )
        )
    else:
        terminal_message(
            conjoin(
                f"Reply sent to {conversation.type} {conversation.id}",
                f"  Message: {reply_msg.id}",
                f"  Priority: {reply_msg.priority}",
            ),
            subject="Done",
            subject_color="green",
        )


@app.command()
@handle_errors("Failed to acknowledge message", handle_exc_class=SiteNineError)
def ack(
    message_id: Annotated[str, typer.Argument(help="Message ID to acknowledge")],
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")] = False,
) -> None:
    """Acknowledge a message as read/processed.

    Marks a message as acknowledged by the current mission, indicating
    that the message has been read and processed. This improves
    accountability and workflow coordination between agents.
    """
    db_path = require_db_path()

    with Database(db_path) as db:
        mission_id = _get_current_mission_id(db)
        msg_manager = MessageManager(db)

        # Verify message exists and acknowledge it
        msg_manager.acknowledge_message(message_id, mission_id)

        # Get message details for output
        message = msg_manager.get_message(message_id)
        CLIError.require_condition(message is not None, f"Message {message_id} not found")
        assert message is not None

    if json_output:
        output_json(
            format_json_response(
                {
                    "message_id": message_id,
                    "mission_id": mission_id,
                    "acknowledged": True,
                }
            )
        )
    else:
        terminal_message(
            conjoin(
                f"✅ Acknowledged message {message_id}",
                "",
                f'  Subject: "{message.subject}"',
                f"  From: Mission #{message.from_possession_id}",
            ),
            subject="Done",
            subject_color="green",
        )


@app.command()
@handle_errors("Failed to show inbox", handle_exc_class=SiteNineError)
def inbox(
    all_conversations: Annotated[bool, typer.Option("--all", "-a", help="Show all conversations")] = False,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")] = False,
) -> None:
    """Show unread messages (default) or all conversations."""
    db_path = require_db_path()

    with Database(db_path) as db:
        mission_id = _get_current_mission_id(db)
        msg_manager = MessageManager(db)

        # Check desk mode status
        mission_mgr = PossessionManager(db)
        mission = mission_mgr.get_possession(mission_id)
        desk_mode = bool(mission and mission.desk_mode_active)

        if all_conversations:
            # Get all conversations where mission is a participant or in scope
            conversations = msg_manager.list_conversations()
            # Filter to only those relevant to this mission
            relevant_convs = []
            for conv in conversations:
                if conv.is_conversation():
                    if mission_id in [conv.participant_1_id, conv.participant_2_id]:
                        relevant_convs.append(conv)
                else:  # discussion
                    if msg_manager.is_possession_in_discussion_scope(conv.id, mission_id):
                        relevant_convs.append(conv)
            conversations = relevant_convs
        else:
            # Get unread conversations
            conversations = msg_manager.get_unread_conversations(mission_id)

        # Pre-compute unread counts and message summaries while DB is open
        conv_unread_counts: dict[str, int] = {}
        inbox_messages: list[dict] = []
        for conv in conversations:
            if not all_conversations:
                unread_msgs = msg_manager.get_unread_messages(conv.id, mission_id)
                conv_unread_counts[conv.id] = len(unread_msgs)
                for msg in unread_msgs:
                    inbox_messages.append(
                        {
                            "message_id": msg.id,
                            "from_mission_id": msg.from_possession_id,
                            "subject": msg.subject,
                            "priority": msg.priority,
                            "conversation_id": conv.id,
                        }
                    )

    if json_output:
        output_json(
            format_json_response(
                {
                    "desk_mode_active": desk_mode,
                    "mission_id": mission_id,
                    "conversations": [
                        {
                            "id": conv.id,
                            "type": conv.type,
                            "subject": conv.subject,
                            "status": conv.status,
                            "unread_count": conv_unread_counts.get(conv.id, 0),
                        }
                        for conv in conversations
                    ],
                    "unread_messages": inbox_messages,
                    "count": len(conversations),
                }
            )
        )
    else:
        # Show desk mode status banner
        if desk_mode:
            console.print("[green]Desk mode: ACTIVE[/green] - monitoring for messages")
        else:
            console.print("[dim]Desk mode: inactive[/dim] (use 's9 comms desk' to enable)")

        if not conversations:
            terminal_message(
                "No unread conversations" if not all_conversations else "No conversations found",
                subject="Info",
                subject_color="blue",
            )
            return

        table = Table(title="Inbox" if not all_conversations else "All Conversations")
        table.add_column("ID", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Subject", style="white")
        table.add_column("Status", style="yellow")
        if not all_conversations:
            table.add_column("Unread", style="red")

        for conv in conversations:
            row = [
                conv.id,
                conv.type,
                conv.subject[:50] + "..." if len(conv.subject) > 50 else conv.subject,
                conv.status,
            ]
            if not all_conversations:
                row.append(str(conv_unread_counts.get(conv.id, 0)))
            table.add_row(*row)

        console.print(table)


@app.command()
@handle_errors("Failed to show conversation", handle_exc_class=SiteNineError)
def show(
    conversation_id: Annotated[str, typer.Argument(help="Conversation/discussion/message ID")],
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")] = False,
) -> None:
    """Show a conversation/discussion or specific message with context.

    Can accept:
    - Conversation ID (CONV-XXXX): Shows entire conversation
    - Message ID (MSG-X-XXXX): Shows message in context
    """
    db_path = require_db_path()

    with Database(db_path) as db:
        mission_id = _get_current_mission_id(db)
        msg_manager = MessageManager(db)

        # Check if it's a message ID or conversation ID
        if conversation_id.startswith("MSG-"):
            # It's a message, get its conversation
            message = msg_manager.get_message(conversation_id)
            CLIError.require_condition(message is not None, f"Message {conversation_id} not found")
            assert message is not None
            conv_id = message.conversation_id
        else:
            conv_id = conversation_id

        # Get conversation
        conversation = msg_manager.get_conversation(conv_id)
        CLIError.require_condition(conversation is not None, f"Conversation {conv_id} not found")
        assert conversation is not None

        # Get all messages in conversation
        messages = msg_manager.list_messages(conversation_id=conv_id)

        # Get acknowledgements for all messages
        message_acks: dict[str, list[dict]] = {}
        for msg in messages:
            message_acks[msg.id] = msg_manager.get_message_acknowledgements(msg.id)

        # Update view for current mission
        msg_manager.update_conversation_view(conv_id, mission_id)

    if json_output:
        output_json(
            format_json_response(
                {
                    "conversation": {
                        "id": conversation.id,
                        "type": conversation.type,
                        "subject": conversation.subject,
                        "status": conversation.status,
                        "created_at": conversation.created_at,
                    },
                    "messages": [
                        {
                            "id": msg.id,
                            "from_mission_id": msg.from_possession_id,
                            "subject": msg.subject,
                            "body": msg.body,
                            "priority": msg.priority,
                            "parent_message_id": msg.parent_message_id,
                            "created_at": msg.created_at,
                            "acknowledgements": message_acks.get(msg.id, []),
                        }
                        for msg in messages
                    ],
                }
            )
        )
    else:
        # Display conversation header
        console.print(f"\n[cyan bold]{conversation.type.upper()}: {conversation.id}[/cyan bold]")
        console.print(f"[white]Subject: {conversation.subject}[/white]")
        console.print(f"[yellow]Status: {conversation.status}[/yellow]")
        console.print()

        # Display messages
        for msg in messages:
            indent = "  " if msg.parent_message_id else ""
            console.print(f"{indent}[cyan]{msg.id}[/cyan] - [magenta]Mission {msg.from_possession_id}[/magenta]")
            console.print(f"{indent}[yellow]Priority: {msg.priority}[/yellow] | [dim]{msg.created_at}[/dim]")

            # Show acknowledgements if any
            acks = message_acks.get(msg.id, [])
            if acks:
                ack_str = f"{len(acks)} ack" + ("s" if len(acks) > 1 else "")
                ack_names = ", ".join([f"{a['daemon_name']} ({a['role']})" for a in acks[:3]])
                if len(acks) > 3:
                    ack_names += f", +{len(acks) - 3} more"
                console.print(f"{indent}[green]✓ {ack_str}: {ack_names}[/green]")

            console.print(f"{indent}[white bold]{msg.subject}[/white bold]")
            console.print()
            # Render markdown body with indent
            md = Markdown(msg.body)
            for line in md.__rich_console__(console, console.options):
                console.print(f"{indent}{line}")
            console.print()


@app.command("list")
@handle_errors("Failed to list conversations", handle_exc_class=SiteNineError)
def list_conversations(
    open_only: Annotated[bool, typer.Option("--open", "-o", help="Show only open conversations")] = False,
    conversation_type: Annotated[str | None, typer.Option("--type", "-t", help="Filter by type")] = None,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")] = False,
) -> None:
    """List all conversations and discussions."""
    db_path = require_db_path()

    with Database(db_path) as db:
        mission_id = _get_current_mission_id(db)
        msg_manager = MessageManager(db)

        status = "open" if open_only else None
        conversations = msg_manager.list_conversations(
            conversation_type=conversation_type,
            status=status,
            possession_id=mission_id if conversation_type == "conversation" else None,
        )

        # For discussions, filter by scope
        if conversation_type != "conversation":
            filtered = []
            for conv in conversations:
                if conv.is_conversation():
                    if mission_id in [conv.participant_1_id, conv.participant_2_id]:
                        filtered.append(conv)
                else:
                    if msg_manager.is_possession_in_discussion_scope(conv.id, mission_id):
                        filtered.append(conv)
            conversations = filtered

    if json_output:
        output_json(
            format_json_response(
                [
                    {
                        "id": conv.id,
                        "type": conv.type,
                        "subject": conv.subject,
                        "status": conv.status,
                        "created_at": conv.created_at,
                        "updated_at": conv.updated_at,
                    }
                    for conv in conversations
                ],
                count=len(conversations),
            )
        )
    else:
        if not conversations:
            terminal_message("No conversations found", subject="Info", subject_color="blue")
            return

        table = Table(title="Conversations & Discussions")
        table.add_column("ID", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Subject", style="white")
        table.add_column("Status", style="yellow")
        table.add_column("Updated", style="dim")

        for conv in conversations:
            table.add_row(
                conv.id,
                conv.type,
                conv.subject[:40] + "..." if len(conv.subject) > 40 else conv.subject,
                conv.status,
                str(conv.updated_at)[:16] if conv.updated_at else "",
            )

        console.print(table)


@app.command()
@handle_errors("Failed to close conversation", handle_exc_class=SiteNineError)
def close(
    conversation_id: Annotated[str, typer.Argument(help="Conversation/discussion ID to close")],
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")] = False,
) -> None:
    """Close a conversation or discussion."""
    db_path = require_db_path()

    with Database(db_path) as db:
        msg_manager = MessageManager(db)
        conversation = msg_manager.close_conversation(conversation_id)

    if json_output:
        output_json(
            format_json_response(
                {
                    "id": conversation.id,
                    "status": conversation.status,
                    "closed_at": conversation.closed_at,
                }
            )
        )
    else:
        terminal_message(
            conjoin(
                f"{conversation.type.title()} {conversation_id} closed",
                f"  Closed at: {conversation.closed_at}",
            ),
            subject="Done",
            subject_color="green",
        )


@app.command()
@handle_errors("Failed to get message status", handle_exc_class=SiteNineError)
def status(
    conversation_id: Annotated[str, typer.Argument(help="Conversation/discussion ID")],
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")] = False,
) -> None:
    """Show who has viewed a conversation/discussion."""
    db_path = require_db_path()

    with Database(db_path) as db:
        msg_manager = MessageManager(db)

        # Get conversation
        conversation = msg_manager.get_conversation(conversation_id)
        CLIError.require_condition(conversation is not None, f"Conversation {conversation_id} not found")

        # Get viewers
        viewers = msg_manager.get_conversation_viewers(conversation_id)

    if json_output:
        output_json(format_json_response(viewers, count=len(viewers)))
    else:
        if not viewers:
            terminal_message(f"No one has viewed {conversation_id} yet", subject="Info", subject_color="blue")
            return

        table = Table(title=f"Viewers of {conversation_id}")
        table.add_column("Possession", style="cyan")
        table.add_column("Daemon", style="magenta")
        table.add_column("Role", style="yellow")
        table.add_column("Last Viewed", style="dim")

        for viewer in viewers:
            table.add_row(
                str(viewer["possession_id"]),
                viewer["daemon_name"],
                viewer["role"],
                viewer["last_viewed_at"][:16] if viewer["last_viewed_at"] else "",
            )

        console.print(table)


@app.command()
@handle_errors("Failed to manage desk mode", handle_exc_class=SiteNineError)
def desk(
    stop: Annotated[bool, typer.Option("--stop", help="Stop desk mode")] = False,
    start: Annotated[bool, typer.Option("--start", help="Start desk mode (default)")] = False,
    mission_id: Annotated[
        int | None, typer.Option("--mission", "-m", help="Possession ID (defaults to current)")
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")] = False,
) -> None:
    """Enable/disable desk mode for receiving questions from other agents.

    Desk mode advertises your possession as available for questions.
    When started, it runs a monitoring loop that checks for new messages
    every 30 seconds and outputs status.

    Usage:
      s9 comms desk              # Start desk mode (default)
      s9 comms desk --start      # Explicit start
      s9 comms desk --stop       # Stop desk mode
    """
    import signal
    import time

    db_path = require_db_path()

    with Database(db_path) as db:
        mid = mission_id if mission_id is not None else _get_current_mission_id(db)
        possession_mgr = PossessionManager(db)

        possession = possession_mgr.get_possession(mid)
        CLIError.require_condition(possession is not None, f"Possession #{mid} not found")
        assert possession is not None
        CLIError.require_condition(
            possession.end_time is None,
            f"Possession #{mid} has already ended",
        )

        if stop:
            # Stop desk mode
            possession_mgr.set_desk_mode(mid, active=False)
            if json_output:
                output_json(format_json_response({"mission_id": mid, "desk_mode_active": False}))
            else:
                terminal_message(
                    "Desk mode disabled",
                    subject="Done",
                    subject_color="green",
                )
            return

        # Start desk mode
        possession_mgr.set_desk_mode(mid, active=True)

        scope_label = f"epic {possession.epic_id}" if possession.epic_id else "all"

    if json_output:
        # In JSON mode, just enable and report status once (no polling loop)
        with Database(db_path) as db:
            msg_manager = MessageManager(db)
            conversations = msg_manager.get_unread_conversations(mid)

            # Collect unread message summaries for inbox display (exclude own messages)
            unread_messages = []
            for conv in conversations:
                for msg in msg_manager.get_unread_messages(conv.id, mid):
                    if msg.from_possession_id != mid:
                        unread_messages.append(
                            {
                                "message_id": msg.id,
                                "from_mission_id": msg.from_possession_id,
                                "subject": msg.subject,
                                "priority": msg.priority,
                                "conversation_id": conv.id,
                            }
                        )

        output_json(
            format_json_response(
                {
                    "mission_id": mid,
                    "desk_mode_active": True,
                    "scope": scope_label,
                    "unread_count": len(unread_messages),
                    "unread_messages": unread_messages,
                }
            )
        )
        return

    terminal_message(
        conjoin(
            f"Desk mode enabled for {scope_label}",
            "Monitoring for messages (checking every 30s)...",
            "",
            "Press Ctrl+C to stop desk mode.",
        ),
        subject="Desk Mode",
        subject_color="green",
    )

    # Set up signal handler for clean exit
    def _handle_interrupt(sig: int, frame: object) -> None:
        console.print()  # newline after ^C
        with Database(db_path) as db:
            possession_mgr = PossessionManager(db)
            possession_mgr.set_desk_mode(mid, active=False)
        terminal_message("Desk mode disabled", subject="Done", subject_color="green")
        raise SystemExit(0)

    signal.signal(signal.SIGINT, _handle_interrupt)

    # Polling loop — inbox-style display per ADR-009 lines 160-171
    while True:
        time.sleep(30)

        with Database(db_path) as db:
            msg_manager = MessageManager(db)
            conversations = msg_manager.get_unread_conversations(mid)

            if conversations:
                lines = _format_desk_inbox_summary(msg_manager, conversations, mid)
                if lines:
                    for line in lines:
                        console.print(line)
                else:
                    console.print("Checking comms... No new messages. (0 unread)")
            else:
                console.print("Checking comms... No new messages. (0 unread)")
