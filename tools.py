"""
Tools for the easydo.ai agent to use.
Each tool should be implemented as a class or function in the available_tools directory.
"""

import os
import importlib
from typing import List, Optional
from langchain.tools import Tool

AVAILABLE_TOOLS_DIR = "available_tools"


def get_tools(selected_tools: Optional[List[str]] = None) -> List[Tool]:
    """
    Dynamically load tools from the available_tools directory.
    Each tool module should define a `get_tool()` function that returns a Tool instance.

    Args:
        selected_tools: List of tool names to include. If None, all tools are included.
    """
    all_tools = []

    # Load all available tools
    for filename in os.listdir(AVAILABLE_TOOLS_DIR):
        if filename.endswith(".py") and not filename.startswith("__"):
            module_name = f"{AVAILABLE_TOOLS_DIR}.{filename[:-3]}"
            try:
                module = importlib.import_module(module_name)
                if hasattr(module, "get_tool"):
                    tool = module.get_tool()
                    all_tools.append(tool)
            except Exception as e:
                print(f"Error loading tool {module_name}: {e}")

    # Filter tools based on selection
    if selected_tools is None:
        return all_tools

    # Filter tools by name
    filtered_tools = []
    for tool in all_tools:
        if tool.name in selected_tools:
            filtered_tools.append(tool)

    print(
        f"Filtered tools: {[tool.name for tool in filtered_tools]} from selected: {selected_tools}"
    )
    return filtered_tools


def get_available_tool_names() -> List[str]:
    """Get a list of all available tool names"""
    tool_names = []
    for filename in os.listdir(AVAILABLE_TOOLS_DIR):
        if filename.endswith(".py") and not filename.startswith("__"):
            module_name = f"{AVAILABLE_TOOLS_DIR}.{filename[:-3]}"
            try:
                module = importlib.import_module(module_name)
                if hasattr(module, "get_tool"):
                    tool = module.get_tool()
                    tool_names.append(tool.name)
            except Exception as e:
                print(f"Error loading tool {module_name}: {e}")
    return tool_names
