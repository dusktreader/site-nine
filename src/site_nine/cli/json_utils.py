"""JSON output utilities for CLI commands"""

import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel
from rich.console import Console

console = Console()


def to_json_serializable(obj: Any) -> Any:
    """Convert object to JSON-serializable format

    Args:
        obj: Object to convert

    Returns:
        JSON-serializable representation
    """
    # Handle Pydantic models
    if isinstance(obj, BaseModel):
        return obj.model_dump()

    # Handle datetime objects
    if isinstance(obj, datetime):
        return obj.isoformat()

    # Handle lists/tuples
    if isinstance(obj, (list, tuple)):
        return [to_json_serializable(item) for item in obj]

    # Handle dicts
    if isinstance(obj, dict):
        return {key: to_json_serializable(value) for key, value in obj.items()}

    # Return as-is for primitives
    return obj


def format_json_response(
    data: Any,
    count: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Format a standard JSON response

    Args:
        data: The main data payload (list, dict, or single object)
        count: Optional count of items (auto-calculated for lists)
        metadata: Optional additional metadata to include

    Returns:
        Formatted JSON response dict
    """
    response: dict[str, Any] = {}

    # Convert data to JSON-serializable format
    data = to_json_serializable(data)

    # Add main data
    if isinstance(data, list):
        response["data"] = data
        response["count"] = count if count is not None else len(data)
    else:
        response["data"] = data
        if count is not None:
            response["count"] = count

    # Add timestamp
    response["timestamp"] = datetime.now().isoformat()

    # Add any additional metadata
    if metadata:
        response["metadata"] = metadata

    return response


def format_json_error(
    error_message: str,
    error_code: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Format a standard JSON error response

    Args:
        error_message: Human-readable error message
        error_code: Optional error code
        details: Optional additional error details

    Returns:
        Formatted JSON error response
    """
    response = {
        "status": "error",
        "error": error_message,
        "timestamp": datetime.now().isoformat(),
    }

    if error_code:
        response["error_code"] = error_code

    if details:
        response["details"] = to_json_serializable(details)

    return response


def output_json(data: dict[str, Any], pretty: bool = False) -> None:
    """Output JSON to console

    Args:
        data: JSON-serializable dict to output
        pretty: Whether to pretty-print with indentation
    """
    if pretty:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(data, ensure_ascii=False))
