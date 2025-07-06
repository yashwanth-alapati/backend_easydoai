from typing import Dict, Any, Optional
from enum import Enum


class ToolPermission(Enum):
    ALWAYS_ALLOW = "always_allow"  # No approval needed
    REQUIRE_APPROVAL = "require_approval"  # Requires user approval
    BLOCKED = "blocked"  # Not allowed to use


# Define which tools require approval
TOOL_PERMISSIONS: Dict[str, ToolPermission] = {
    # Gmail MCP tools
    "gmail_mcp": {
        "send_email": ToolPermission.REQUIRE_APPROVAL,
        "draft_email": ToolPermission.ALWAYS_ALLOW,
        "read_email": ToolPermission.ALWAYS_ALLOW,
        "search_emails": ToolPermission.ALWAYS_ALLOW,
        "modify_email": ToolPermission.REQUIRE_APPROVAL,
        "delete_email": ToolPermission.REQUIRE_APPROVAL,
        "list_email_labels": ToolPermission.ALWAYS_ALLOW,
        "create_label": ToolPermission.REQUIRE_APPROVAL,
        "update_label": ToolPermission.REQUIRE_APPROVAL,
        "delete_label": ToolPermission.REQUIRE_APPROVAL,
        "batch_modify_emails": ToolPermission.REQUIRE_APPROVAL,
        "batch_delete_emails": ToolPermission.REQUIRE_APPROVAL,
    },
    # Add other tools here with their permissions
}


def requires_approval(tool_name: str, subtool: Optional[str] = None) -> bool:
    """Check if a tool requires user approval."""
    if tool_name not in TOOL_PERMISSIONS:
        return True  # Default to requiring approval for unknown tools

    if isinstance(TOOL_PERMISSIONS[tool_name], dict):
        if subtool is None:
            return (
                True  # Require approval if subtool not specified for tool with subtools
            )
        return (
            TOOL_PERMISSIONS[tool_name].get(subtool, ToolPermission.REQUIRE_APPROVAL)
            == ToolPermission.REQUIRE_APPROVAL
        )

    return TOOL_PERMISSIONS[tool_name] == ToolPermission.REQUIRE_APPROVAL


def format_approval_request(tool_name: str, tool_args: Dict[str, Any]) -> str:
    """Format a user-friendly approval request message."""
    if tool_name == "gmail_mcp":
        subtool = tool_args.get("tool")
        args = tool_args.get("args", {})

        if subtool == "send_email":
            return (
                f"Request to send email:\n"
                f"To: {args.get('to', [])}\n"
                f"Subject: {args.get('subject', '')}\n"
                f"CC: {args.get('cc', [])}\n"
                f"BCC: {args.get('bcc', [])}"
            )

        elif subtool == "delete_email":
            return f"Request to delete email with ID: {args.get('messageId', '')}"

        elif subtool in ["modify_email", "batch_modify_emails"]:
            return (
                f"Request to modify email(s):\n"
                f"Add labels: {args.get('addLabelIds', [])}\n"
                f"Remove labels: {args.get('removeLabelIds', [])}"
            )

    # Default format for unknown tools
    return f"Request to use {tool_name} with arguments: {tool_args}"
