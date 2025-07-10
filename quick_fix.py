#!/usr/bin/env python3
"""
Quick fix for remaining linting issues
"""

import os
import re

def fix_agents_line_length():
    """Fix the long line in agents.py"""
    if os.path.exists("agents.py"):
        with open("agents.py", 'r') as f:
            content = f.read()
        
        # Fix the long logger line
        old_line = ('            logger.info(\n'
                   '                f"LLM requested tool calls: {[tc[\'name\'] for tc in response.tool_calls]}"\n'
                   '            )')
        
        new_line = ('            tool_names = [tc[\'name\'] for tc in response.tool_calls]\n'
                   '            logger.info(f"LLM requested tool calls: {tool_names}")')
        
        content = content.replace(old_line, new_line)
        
        with open("agents.py", 'w') as f:
            f.write(content)
        print("✓ Fixed line length in agents.py")

def fix_gmail_mcp_line_length():
    """Fix the long line in available_tools/gmail_mcp.py"""
    if os.path.exists("available_tools/gmail_mcp.py"):
        with open("available_tools/gmail_mcp.py", 'r') as f:
            content = f.read()
        
        # Break the long description line
        old_desc = ('description="Access Gmail via Lambda MCP server. Actions: get_messages (query, max_results), '
                   'send_message (to, subject, body), list_tools. Always requires user_id.",')
        
        new_desc = ('description=(\n'
                   '            "Access Gmail via Lambda MCP server. "\n'
                   '            "Actions: get_messages (query, max_results), send_message (to, subject, body), "\n'
                   '            "list_tools. Always requires user_id."\n'
                   '        ),')
        
        content = content.replace(old_desc, new_desc)
        
        with open("available_tools/gmail_mcp.py", 'w') as f:
            f.write(content)
        print("✓ Fixed line length in available_tools/gmail_mcp.py")

def fix_calendar_server_syntax():
    """Fix syntax errors in calendar_server.py"""
    if os.path.exists("lambda_mcp_servers/calendar_lambda/calendar_server.py"):
        with open("lambda_mcp_servers/calendar_lambda/calendar_server.py", 'r') as f:
            content = f.read()
        
        # Fix the syntax errors - these seem to be from incorrect replacements
        fixes = [
            # Fix line 89
            ('calendars = calendars_result.get("items", []) _ = f"Found {len(calendars)} calendars:\\n\\n"',
             'calendars = calendars_result.get("items", [])\n    result = f"Found {len(calendars)} calendars:\\n\\n"'),
            
            # Fix line 130  
            ('return "No upcoming events found." _ = f"Found {len(events)} events:\\n\\n"',
             'return "No upcoming events found."\n    result = f"Found {len(events)} events:\\n\\n"'),
            
            # Fix line 252
            ('body _ = event.get("httpMethod", "POST")',
             'http_method = event.get("httpMethod", "POST")'),
        ]
        
        for old, new in fixes:
            content = content.replace(old, new)
        
        with open("lambda_mcp_servers/calendar_lambda/calendar_server.py", 'w') as f:
            f.write(content)
        print("✓ Fixed syntax errors in lambda_mcp_servers/calendar_lambda/calendar_server.py")

def main():
    """Run all quick fixes"""
    print("🔧 Running quick fixes for remaining linting issues...\n")
    
    fix_agents_line_length()
    fix_gmail_mcp_line_length()
    fix_calendar_server_syntax()
    
    print("\n✅ Quick fixes completed!")
    print("Run 'flake8 .' to verify the fixes")

if __name__ == "__main__":
    main() 