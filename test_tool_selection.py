"""
Test script to verify tool selection functionality
"""

import asyncio
import os
from agents import EasydoAgent
from tools import get_tools, get_available_tool_names

async def test_tool_selection():
    """Test that tool selection works correctly"""
    print("🔧 Testing Tool Selection Feature")
    print("=" * 50)
    
    # Test 1: Get all available tools
    print("\n1. Testing get_available_tool_names:")
    all_tools = get_available_tool_names()
    print(f"   Available tools: {all_tools}")
    
    # Test 2: Get tools with no selection (should return all)
    print("\n2. Testing get_tools() with no selection:")
    tools_no_selection = get_tools()
    print(f"   Tools loaded: {[tool.name for tool in tools_no_selection]}")
    
    # Test 3: Get tools with specific selection
    print("\n3. Testing get_tools() with specific selection:")
    selected_tools = ["web_search", "gmail_mcp"]
    tools_with_selection = get_tools(selected_tools)
    print(f"   Selected tools: {selected_tools}")
    print(f"   Tools loaded: {[tool.name for tool in tools_with_selection]}")
    
    # Test 4: Get tools with invalid selection
    print("\n4. Testing get_tools() with invalid selection:")
    invalid_selection = ["invalid_tool", "another_invalid"]
    tools_invalid = get_tools(invalid_selection)
    print(f"   Invalid selection: {invalid_selection}")
    print(f"   Tools loaded: {[tool.name for tool in tools_invalid]}")
    
    # Test 5: Test agent with tool selection
    print("\n5. Testing EasydoAgent with tool selection:")
    agent_with_tools = EasydoAgent(selected_tools=["web_search"])
    print(f"   Agent tools: {[tool.name for tool in agent_with_tools.tools]}")
    
    # Test 6: Test agent with no tools
    print("\n6. Testing EasydoAgent with no tools:")
    agent_no_tools = EasydoAgent(selected_tools=[])
    print(f"   Agent tools: {[tool.name for tool in agent_no_tools.tools]}")
    
    # Test 7: Test agent response with limited tools
    print("\n7. Testing agent response with limited tools:")
    try:
        response = await agent_with_tools.process_message(
            "Search for the best Mexican restaurants in New York",
            user_id="test_user"
        )
        print(f"   Response: {response[:100]}...")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n" + "=" * 50)
    print("✅ Tool selection test completed!")

if __name__ == "__main__":
    asyncio.run(test_tool_selection()) 