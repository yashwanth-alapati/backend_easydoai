"""
Tools for the easydo.ai agent to use.
Each tool should be implemented as a class or function in the available_tools directory.
"""

import os
import importlib
from typing import List
from langchain.tools import Tool

AVAILABLE_TOOLS_DIR = "available_tools"

def get_tools() -> List[Tool]:
    """
    Dynamically load all tools from the available_tools directory.
    Each tool module should define a `get_tool()` function that returns a Tool instance.
    """
    tools = []
    for filename in os.listdir(AVAILABLE_TOOLS_DIR):
        if filename.endswith(".py") and not filename.startswith("__"):
            module_name = f"{AVAILABLE_TOOLS_DIR}.{filename[:-3]}"
            module = importlib.import_module(module_name)
            if hasattr(module, "get_tool"):
                tools.append(module.get_tool())
    return tools