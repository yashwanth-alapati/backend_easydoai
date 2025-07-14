"""
Multi-agent supervisor system for easydo.ai
"""

import logging
from typing import Dict, Any, List, Sequence, TypedDict, Optional, Annotated
from langchain_anthropic import ChatAnthropic
from langchain.schema import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.messages import ToolMessage
from langgraph.graph import StateGraph, END, MessagesState, START
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command
from langchain_core.tools import tool, InjectedToolCallId, Tool
from langgraph.prebuilt import InjectedState
from tools import get_tools
from datetime import datetime, date
import json
import os
from dotenv import load_dotenv

# Add these imports for timezone correction
from dateutil import parser
import pytz

# Improved logging configuration
def setup_logging():
    """Setup improved logging with better formatting and filtering"""
    
    # Custom formatter for more readable logs
    class ColoredFormatter(logging.Formatter):
        """Custom formatter with colors and better structure"""
        
        # Color codes
        COLORS = {
            'DEBUG': '\033[36m',     # Cyan
            'INFO': '\033[32m',      # Green  
            'WARNING': '\033[33m',   # Yellow
            'ERROR': '\033[31m',     # Red
            'CRITICAL': '\033[35m',  # Magenta
            'RESET': '\033[0m'       # Reset
        }
        
        def format(self, record):
            # Add color to level name
            if record.levelname in self.COLORS:
                record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"
            
            # Truncate long messages
            if len(record.getMessage()) > 200:
                record.msg = record.getMessage()[:200] + "..."
            
            return super().format(record)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Clear any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler with custom formatter
    console_handler = logging.StreamHandler()
    formatter = ColoredFormatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)-15s | %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Configure specific loggers
    # Reduce HTTP request verbosity
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    # Our application loggers
    logging.getLogger("easydoai.agent").setLevel(logging.INFO)
    logging.getLogger("chat_service").setLevel(logging.INFO)
    
    return logging.getLogger("easydoai.agent")

# Setup logging at module level
logger = setup_logging()


class AgentState(TypedDict):
    messages: Sequence[BaseMessage]
    next_action: str
    tool_results: List[Any]
    user_context: Dict[str, Any]


def create_json_gmail_tool():
    """Create a Gmail tool that accepts a single JSON string"""
    
    def gmail_send_email_json(json_input: str) -> Any:
        """
        Gmail send email function that accepts a JSON string
        """
        logger.info(f"📧 GMAIL TOOL: Processing email request")
        try:
            # Parse the JSON input
            input_data = json.loads(json_input)
            logger.info(f"📧 GMAIL TOOL: Sending to {input_data.get('to', 'unknown')}")
            
            # Get the original Gmail tool
            gmail_tools = get_tools(["gmail_mcp"])
            if not gmail_tools:
                logger.error("📧 GMAIL TOOL: Gmail tool not available")
                return {"status": "error", "message": "Gmail tool not available"}
            
            gmail_tool = gmail_tools[0]
            
            # Call the original Gmail tool with the parsed data
            try:
                result = gmail_tool.func(**input_data)
                logger.info(f"📧 GMAIL TOOL: Email sent successfully")
                return result
            except Exception as e:
                logger.error(f"📧 GMAIL TOOL: Error - {str(e)}")
                return {"status": "error", "message": f"Gmail tool error: {str(e)}"}
                
        except json.JSONDecodeError as e:
            logger.error(f"📧 GMAIL TOOL: JSON decode error - {str(e)}")
            return {"status": "error", "message": f"Invalid JSON input: {str(e)}"}
        except Exception as e:
            logger.error(f"📧 GMAIL TOOL: General error - {str(e)}")
            return {"status": "error", "message": f"Error processing request: {str(e)}"}
    
    return Tool(
        name="gmail_send_email",
        description=(
            "Send an email using Gmail. "
            "Provide a JSON string with: {\"action\": \"send_message\", \"user_id\": \"...\", \"to\": \"...\", \"subject\": \"...\", \"body\": \"...\"}. "
            "Use this tool to send emails to recipients."
        ),
        func=gmail_send_email_json,
    )


def create_json_calendar_tool():
    """Create a Calendar tool that accepts a single JSON string"""
    
    def calendar_tool_json(json_input: str) -> Any:
        """
        Calendar tool function that accepts a JSON string
        """
        logger.info(f"📅 CALENDAR TOOL: Processing calendar request")
        try:
            # Parse the JSON input
            input_data = json.loads(json_input)
            logger.info(f"📅 CALENDAR TOOL: Operation - {input_data.get('tool', 'unknown')}")
            
            # Get the original Calendar tool
            calendar_tools = get_tools(["google_calendar_mcp"])
            if not calendar_tools:
                logger.error("📅 CALENDAR TOOL: Calendar tool not available")
                return {"status": "error", "message": "Calendar tool not available"}
            
            calendar_tool = calendar_tools[0]
            
            # Extract tool and args from the input
            tool_name = input_data.get("tool")
            args = input_data.get("args", {})
            
            # Add user_id to args if it's in the input
            if "user_id" in input_data:
                args["user_id"] = input_data["user_id"]
            
            # Call the original Calendar tool with the correct structure
            try:
                result = calendar_tool.func(tool=tool_name, args=args)
                logger.info(f"📅 CALENDAR TOOL: Calendar operation completed successfully")
                return result
            except Exception as e:
                logger.error(f"📅 CALENDAR TOOL: Error - {str(e)}")
                return {"status": "error", "message": f"Calendar tool error: {str(e)}"}
                
        except json.JSONDecodeError as e:
            logger.error(f"📅 CALENDAR TOOL: JSON decode error - {str(e)}")
            return {"status": "error", "message": f"Invalid JSON input: {str(e)}"}
        except Exception as e:
            logger.error(f"📅 CALENDAR TOOL: General error - {str(e)}")
            return {"status": "error", "message": f"Error processing request: {str(e)}"}
    
    return Tool(
        name="google_calendar_mcp",
        description=(
            "Manage Google Calendar events. "
            "Provide a JSON string with: {\"tool\": \"create-event\", \"user_id\": \"...\", \"args\": {\"summary\": \"...\", \"start\": \"...\", \"end\": \"...\", \"attendees\": [{\"email\": \"...\"}]}}. "
            "Use this tool to create, update, or manage calendar events."
        ),
        func=calendar_tool_json,
    )


class MultiAgentSupervisor:
    """Multi-agent supervisor system with retriever and executor agents"""

    def __init__(self, selected_tools: Optional[List[str]] = None):
        logger.info("🚀 Initializing Multi-Agent Supervisor")
        self.llm = ChatAnthropic(
            model="claude-3-5-haiku-20241022",
            temperature=0.7,
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        )
        logger.info("✅ Claude model loaded")

        # Create specialized agents
        self.retriever_agent = self._create_retriever_agent()
        self.executor_agent = self._create_executor_agent()
        self.supervisor_agent = self._create_supervisor_agent()
        
        # Build the multi-agent graph
        self.graph = self._build_supervisor_graph()
        logger.info("✅ Multi-agent system ready")

    def _create_retriever_agent(self):
        """Create retriever agent with web search capabilities"""
        # Get web search tool - use correct tool name
        web_search_tools = get_tools(["web_search"])
        
        # Add report to supervisor tool
        report_to_supervisor = self._create_report_to_supervisor_tool()
        all_tools = web_search_tools + [report_to_supervisor]
        
        retriever_agent = create_react_agent(
            model=self.llm,
            tools=all_tools,
            prompt=(
                "You are a retriever agent specialized in information gathering and research.\n\n"
                "INSTRUCTIONS:\n"
                "1. Decide which tool to use based on the user's request\n"
                "2. Look at the description of the tool and see if you have all details required\n"
                "3. If you have all required details, proceed to calling those tools\n"
                "4. If you don't have all required details, or if the task is outside your capabilities "
                "(such as sending emails, creating calendar events, or performing actions), "
                "use report_to_supervisor to ask for more details or hand off the task\n\n"
                "Available tools and their purposes:\n"
                "- Use your available tools for information gathering and research tasks\n"
                "- Use report_to_supervisor when you need more information or when the task "
                "requires actions beyond research (like sending emails or creating events)\n\n"
                "Be thorough but concise in your findings when you can complete the task."
            ),
            name="retriever_agent",
        )
        logger.info("🔍 Retriever agent created")
        return retriever_agent

    def _create_executor_agent(self):
        """Create executor agent with Gmail and Calendar tools"""
        # Create JSON wrapper tools for both Gmail and Calendar
        gmail_tool = create_json_gmail_tool()
        calendar_tool = create_json_calendar_tool()
        
        # Add report to supervisor tool
        report_to_supervisor = self._create_report_to_supervisor_tool()
        
        # Combine tools
        executor_tools = [gmail_tool, calendar_tool, report_to_supervisor]
        
        # Create a generic prompt for the executor agent
        executor_prompt = (
            "You are an executor agent specialized in performing actions and executing tasks.\n\n"
            "INSTRUCTIONS:\n"
            "1. Decide which tool to use based on the user's request\n"
            "2. Look at the description of the tool and see if you have all details required\n"
            "3. If you have all required details, proceed to calling those tools\n"
            "4. If you don't have all required details, or if the task is outside your capabilities "
            "(such as research, information gathering, or web searches), "
            "use report_to_supervisor to ask for more details or hand off the task\n\n"
            "Available tools and their purposes:\n"
            "- Use your available tools for action-oriented tasks like sending emails and managing calendars\n"
            "- Use report_to_supervisor when you need more information or when the task "
            "requires research or information gathering beyond your action capabilities\n\n"
            "Provide clear, actionable results of your operations when you can complete the task."
        )
        
        executor_agent = create_react_agent(
            model=self.llm,
            tools=executor_tools,
            prompt=executor_prompt,
            name="executor_agent",
        )
        logger.info("⚡ Executor agent created")
        return executor_agent

    def _create_supervisor_agent(self):
        """Create supervisor agent that coordinates between retriever and executor"""
        # Create handoff tools for supervisor
        assign_to_retriever = self._create_handoff_tool(
            agent_name="retriever_agent",
            description="Assign research and information gathering tasks to the retriever agent."
        )
        
        assign_to_executor = self._create_handoff_tool(
            agent_name="executor_agent", 
            description="Assign email and calendar management tasks to the executor agent."
        )

        supervisor_agent = create_react_agent(
            model=self.llm,
            tools=[assign_to_retriever, assign_to_executor],
            prompt=(
                "You are a supervisor managing two specialized agents:\n"
                "- RETRIEVER AGENT: Can only perform web searches and information gathering\n"
                "- EXECUTOR AGENT: Can only perform actions like sending emails and creating calendar events\n\n"
                
                "WORKFLOW COORDINATION RULES:\n\n"
                
                "1. FOR PURE RESEARCH TASKS:\n"
                "   - Send directly to retriever agent\n"
                "   - Example: 'find information about...' → retriever_agent\n\n"
                
                "2. FOR PURE ACTION TASKS (with all details provided):\n"
                "   - Send directly to executor agent\n"
                "   - Example: 'send email to john@example.com saying hello' → executor_agent\n\n"
                
                "3. FOR COMBINED TASKS (research + actions):\n"
                "   - FIRST: Send research part to retriever agent\n"
                "   - THEN: Once you have research results, combine them with action requirements and send to executor\n"
                "   - Example: 'find best restaurant and send invite' → retriever first, then executor with restaurant info\n\n"
                
                "4. WHEN AGENTS REPORT BACK:\n"
                "   - If retriever reports back saying it can't do actions BUT hasn't provided research yet:\n"
                "     → Tell retriever: 'First complete the research part using web search, then report back with findings'\n"
                "   - If retriever provides research results and mentions actions needed:\n"
                "     → Take the research results and delegate action tasks to executor with full context\n"
                "   - If executor reports back needing more information:\n"
                "     → Send missing information request to retriever, then back to executor\n\n"
                
                "5. COORDINATION EXAMPLES:\n"
                "   - Task: 'Find best pizza place and send email invitation'\n"
                "     Step 1: 'Retriever: Find the best pizza place in [location]'\n"
                "     Step 2: Wait for research results\n"
                "     Step 3: 'Executor: Send email about [pizza place] invitation with details...'\n\n"
                
                "IMPORTANT INSTRUCTIONS:\n"
                "- NEVER let retriever skip the research step when research is needed\n"
                "- ALWAYS ensure retriever completes web search before moving to actions\n"
                "- ALWAYS provide full context (including research results) to executor\n"
                "- Break down complex tasks into research phase → action phase\n"
                "- If an agent reports inability without completing their core task, guide them to complete it first\n"
                "- Provide comprehensive summaries to users based on all agent results"
            ),
            name="supervisor",
        )
        logger.info("🎯 Supervisor agent created")
        return supervisor_agent

    def _create_handoff_tool(self, *, agent_name: str, description: str | None = None):
        """Create a handoff tool for transferring control to another agent"""
        name = f"transfer_to_{agent_name}"
        description = description or f"Ask {agent_name} for help."

        @tool(name, description=description)
        def handoff_tool(
            state: Annotated[MessagesState, InjectedState],
            tool_call_id: Annotated[str, InjectedToolCallId],
            **kwargs  # Accept any additional arguments
        ) -> Command:
            # Log the handoff with full context
            if kwargs:
                logger.info(f"🔀 SUPERVISOR → {agent_name.upper()}: Delegating with context")
                logger.info(f"   📋 DELEGATION DETAILS:")
                for key, value in kwargs.items():
                    logger.info(f"      {key}: {value}")
            else:
                logger.info(f"🔀 SUPERVISOR → {agent_name.upper()}: Delegating task")
            
            tool_message = {
                "role": "tool",
                "content": f"Successfully transferred to {agent_name}",
                "name": name,
                "tool_call_id": tool_call_id,
            }
            return Command(
                goto=agent_name,
                update={**state, "messages": state["messages"] + [tool_message]},
                graph=Command.PARENT,
            )

        return handoff_tool

    def _create_report_to_supervisor_tool(self):
        """Create a tool for agents to report back to supervisor when they need help or clarification"""
        @tool("report_to_supervisor", description="Report back to supervisor when you need more details, clarification, or when the task is outside your capabilities")
        def report_to_supervisor_tool(
            message: str,
            state: Annotated[MessagesState, InjectedState],
            tool_call_id: Annotated[str, InjectedToolCallId],
        ) -> Command:
            """
            Report back to supervisor with a message
            
            Args:
                message: The message to send to the supervisor explaining what you need
            """
            # Log the report back to supervisor
            logger.info(f"📨 AGENT → SUPERVISOR: {message[:150]}...")
            
            tool_message = {
                "role": "tool",
                "content": f"Agent reporting to supervisor: {message}",
                "name": "report_to_supervisor",
                "tool_call_id": tool_call_id,
            }
            return Command(
                goto="supervisor",
                update={**state, "messages": state["messages"] + [tool_message]},
                graph=Command.PARENT,
            )

        return report_to_supervisor_tool

    def _build_supervisor_graph(self):
        """Build the multi-agent supervisor graph"""
        logger.info("🔧 Building multi-agent graph...")
        
        # Create the supervisor graph
        supervisor_graph = (
            StateGraph(MessagesState)
            .add_node(self.supervisor_agent, destinations=("retriever_agent", "executor_agent", END))
            .add_node(self.retriever_agent)
            .add_node(self.executor_agent)
            .add_edge(START, "supervisor")  # Add the START edge
            .add_edge("retriever_agent", "supervisor")
            .add_edge("executor_agent", "supervisor")
            .compile()
        )
        
        logger.info("✅ Multi-agent graph compiled")
        return supervisor_graph

    def _ensure_iso_with_tz(self, dt_str, tz_str):
        """Ensure datetime string has timezone info, else append from tz_str."""
        try:
            dt = parser.parse(dt_str)
            if not dt.tzinfo:
                tz = pytz.timezone(tz_str)
                dt = tz.localize(dt)
            return dt.isoformat()
        except Exception as e:
            logger.warning(
                f"Could not parse or localize datetime '{dt_str}' with tz '{tz_str}': {e}"
            )
            return dt_str  # fallback to original

    def _extract_text_from_message(self, message):
        """Extract plain text from a message, handling different formats"""
        if isinstance(message.content, str):
            return message.content
        elif isinstance(message.content, list):
            # Handle structured content (like tool calls)
            text_parts = []
            for item in message.content:
                if isinstance(item, dict) and item.get('type') == 'text':
                    text_parts.append(item.get('text', ''))
            return ' '.join(text_parts) if text_parts else ''
        return ''

    async def process_message(
        self,
        user_input: str,
        conversation_history: List[BaseMessage] = None,
        user_id: str = None,
    ) -> str:
        """Process user message through the multi-agent supervisor system"""
        logger.info(f"📝 Processing: {user_input[:100]}{'...' if len(user_input) > 100 else ''}")
        
        if conversation_history is None:
            conversation_history = []
        
        # Add user context to the initial message if user_id is provided
        if user_id:
            user_input_with_context = f"User ID: {user_id}\n\n{user_input}"
        else:
            user_input_with_context = user_input
            
        messages = conversation_history + [HumanMessage(content=user_input_with_context)]
        logger.info(f"🔄 Starting multi-agent workflow with {len(messages)} messages")

        # Create initial state
        initial_state = {
            "messages": messages,
        }

        try:
            # Process through the multi-agent supervisor system
            logger.info("🚀 Starting multi-agent execution...")
            final_state = await self.graph.ainvoke(initial_state)
            
            # Log detailed workflow analysis
            self._log_workflow_analysis(final_state["messages"])
            
            logger.info(f"✅ Workflow completed with {len(final_state['messages'])} total messages")
            
            # Look for the best response from the conversation
            all_responses = []
            
            for message in final_state["messages"]:
                if isinstance(message, AIMessage):
                    text = self._extract_text_from_message(message)
                    if text and text.strip() and text != "[]":
                        all_responses.append({
                            'agent': getattr(message, 'name', 'unknown'),
                            'content': text,
                            'index': len(all_responses)
                        })
            
            # Find the most comprehensive response
            if all_responses:
                # Prefer responses from retriever or executor agents over supervisor delegation messages
                meaningful_responses = [r for r in all_responses if 
                                    (r['agent'] in ['retriever_agent', 'executor_agent'] and 
                                     len(r['content']) > 100) or  # Substantial content
                                    (r['agent'] == 'supervisor' and 
                                     'transfer' not in r['content'].lower())]  # Not a delegation message
                
                if meaningful_responses:
                    best_response = meaningful_responses[-1]
                    logger.info(f"📤 Using {best_response['agent']} response ({len(best_response['content'])} chars)")
                    return best_response['content']
                else:
                    # Fallback to the last response that's not a delegation
                    for response in reversed(all_responses):
                        if 'transfer' not in response['content'].lower():
                            logger.info(f"📤 Using fallback from {response['agent']} ({len(response['content'])} chars)")
                            return response['content']
            
            # If no good response found, create a summary from available information
            if all_responses:
                # Try to combine information from multiple agents
                retriever_info = [r for r in all_responses if r['agent'] == 'retriever_agent']
                executor_info = [r for r in all_responses if r['agent'] == 'executor_agent']
                
                if retriever_info:
                    logger.info("📤 Using retriever information")
                    return retriever_info[-1]['content']
                elif executor_info:
                    logger.info("📤 Using executor information")
                    return executor_info[-1]['content']
                    
        except Exception as e:
            logger.error(f"❌ Multi-agent processing error: {e}")
            return f"I'm sorry, I encountered an error while processing your request: {str(e)}"
            
        logger.warning("⚠️  No AI response found")
        return "I'm sorry, I couldn't generate a response."

    def _log_workflow_analysis(self, messages):
        """Log detailed analysis of the workflow steps"""
        logger.info("🔍 WORKFLOW ANALYSIS:")
        
        step_counter = 1
        current_agent = "supervisor"
        
        for i, message in enumerate(messages):
            if hasattr(message, 'name') and message.name:
                agent_name = message.name
            elif isinstance(message, HumanMessage):
                agent_name = "user"
            else:
                agent_name = "unknown"
            
            # Track agent transitions
            if agent_name != current_agent and agent_name != "user":
                logger.info(f"   🔄 Step {step_counter}: Agent transition → {agent_name.upper()}")
                current_agent = agent_name
                step_counter += 1
            
            # Log tool calls
            if hasattr(message, 'tool_calls') and message.tool_calls:
                for tool_call in message.tool_calls:
                    tool_name = tool_call.get('name', 'unknown')
                    args = tool_call.get('args', {})
                    
                    if tool_name.startswith('transfer_to_'):
                        target_agent = tool_name.replace('transfer_to_', '')
                        logger.info(f"   📤 Step {step_counter}: {agent_name.upper()} → {target_agent.upper()}")
                        if args:
                            logger.info(f"      📋 FULL DELEGATION CONTEXT:")
                            for key, value in args.items():
                                logger.info(f"         {key}: {value}")
                        
                        # Also log the text content of the message if available
                        if hasattr(message, 'content') and isinstance(message.content, list):
                            for content_item in message.content:
                                if isinstance(content_item, dict) and content_item.get('type') == 'text':
                                    text_content = content_item.get('text', '')
                                    if text_content and len(text_content.strip()) > 20:  # Only log substantial text
                                        logger.info(f"      📝 SUPERVISOR INSTRUCTION:")
                                        logger.info(f"         {text_content}")
                                        
                    elif tool_name == 'report_to_supervisor':
                        if 'message' in args:
                            logger.info(f"   📨 Step {step_counter}: {agent_name.upper()} reports to SUPERVISOR")
                            logger.info(f"      💬 FULL AGENT REPORT:")
                            logger.info(f"         {args['message']}")
                            
                    elif tool_name == 'web_search':
                        if 'query' in args:
                            logger.info(f"   🔍 Step {step_counter}: {agent_name.upper()} web search")
                            logger.info(f"      🔎 SEARCH QUERY: {args['query']}")
                            
                    elif tool_name in ['gmail_send_email', 'google_calendar_mcp']:
                        logger.info(f"   ⚡ Step {step_counter}: {agent_name.upper()} executes {tool_name}")
                        if args and '__arg1' in args:
                            try:
                                import json
                                parsed_args = json.loads(args['__arg1'])
                                logger.info(f"      📋 FULL TOOL ARGUMENTS:")
                                if tool_name == 'gmail_send_email':
                                    logger.info(f"         Action: {parsed_args.get('action', 'unknown')}")
                                    logger.info(f"         To: {parsed_args.get('to', 'unknown')}")
                                    logger.info(f"         Subject: {parsed_args.get('subject', 'unknown')}")
                                    logger.info(f"         Body: {parsed_args.get('body', 'unknown')}")
                                elif tool_name == 'google_calendar_mcp':
                                    logger.info(f"         Tool: {parsed_args.get('tool', 'unknown')}")
                                    logger.info(f"         User ID: {parsed_args.get('user_id', 'unknown')}")
                                    args_dict = parsed_args.get('args', {})
                                    for key, value in args_dict.items():
                                        logger.info(f"         {key}: {value}")
                            except Exception as e:
                                logger.info(f"      📋 RAW ARGS: {args}")
                    
                    step_counter += 1
            
            # Log tool results with more detail
            if isinstance(message, ToolMessage):
                logger.info(f"   ✅ Step {step_counter}: Tool result")
                if message.content.startswith('{"status": "success"'):
                    try:
                        import json
                        result_data = json.loads(message.content)
                        logger.info(f"      ✅ SUCCESS DETAILS:")
                        if 'data' in result_data:
                            data = result_data['data']
                            for key, value in data.items():
                                if key == 'html_link':
                                    logger.info(f"         {key}: [LINK PROVIDED]")
                                else:
                                    logger.info(f"         {key}: {value}")
                    except:
                        logger.info(f"      ✅ Success")
                        
                elif message.content.startswith('Agent reporting to supervisor'):
                    # Extract the actual report content
                    report_content = message.content.replace('Agent reporting to supervisor: ', '')
                    logger.info(f"      📨 SUPERVISOR RECEIVED REPORT:")
                    logger.info(f"         {report_content}")
                    
                elif message.content.startswith('Successfully transferred'):
                    logger.info(f"      🔄 Transfer completed")
                    
                else:
                    # For web search results, show more structured output
                    if len(message.content) > 500 and message.content.startswith('[{'):
                        try:
                            import json
                            search_results = json.loads(message.content)
                            logger.info(f"      🔍 WEB SEARCH RESULTS ({len(search_results)} results):")
                            for idx, result in enumerate(search_results[:3]):  # Show first 3 results
                                logger.info(f"         Result {idx+1}:")
                                logger.info(f"           Title: {result.get('title', 'N/A')}")
                                logger.info(f"           URL: {result.get('url', 'N/A')}")
                                content_preview = result.get('content', '')[:200] + "..." if len(result.get('content', '')) > 200 else result.get('content', '')
                                logger.info(f"           Content: {content_preview}")
                        except:
                            content_preview = message.content[:200] + "..." if len(message.content) > 200 else message.content
                            logger.info(f"      📄 RESULT CONTENT: {content_preview}")
                    else:
                        logger.info(f"      📄 RESULT CONTENT: {message.content}")
                        
                step_counter += 1
        
        logger.info("🔚 WORKFLOW ANALYSIS COMPLETE")


# Legacy EasydoAgent class for backward compatibility
class EasydoAgent:
    """Legacy single agent - now delegates to MultiAgentSupervisor"""

    def __init__(self, selected_tools: Optional[List[str]] = None):
        logger.info("Initializing EasydoAgent (legacy mode)")
        self.multi_agent = MultiAgentSupervisor(selected_tools)
        logger.info("EasydoAgent now uses MultiAgentSupervisor")

    async def process_message(
        self,
        user_input: str,
        conversation_history: List[BaseMessage] = None,
        user_id: str = None,
    ) -> str:
        """Delegate to the multi-agent supervisor system"""
        return await self.multi_agent.process_message(
            user_input, conversation_history, user_id
        )
