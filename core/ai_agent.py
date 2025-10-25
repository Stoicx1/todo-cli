"""
TaskAssistantAgent - LangChain ReAct Agent for Task Management

Provides intelligent AI assistant with tool execution capabilities:
- ReAct pattern (Reasoning + Acting)
- Tool orchestration
- Context-aware responses
- Streaming support
"""

from typing import Optional, Callable
from dotenv import load_dotenv
import os

# LangChain 1.0 imports
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from core import ai_tools
from utils.conversation_memory import ConversationMemoryManager
from config import ai as ai_config
from debug_logger import debug_log


class TaskAssistantAgent:
    """
    Intelligent task management assistant powered by LangChain.

    Capabilities:
    - Create, edit, search, and complete tasks via natural language
    - Remember conversation context across sessions
    - Stream responses with markdown formatting
    - Context-aware (knows current filter, view, task stats)
    """

    def __init__(self, state, memory: ConversationMemoryManager, model: Optional[str] = None):
        """
        Initialize task assistant agent.

        Args:
            state: AppState instance for accessing task data
            memory: ConversationMemoryManager for persistent conversations
            model: OpenAI model name (default: from config)
        """
        debug_log.info("[AI_AGENT] Initializing TaskAssistantAgent...")

        try:
            load_dotenv()

            self.state = state
            self.memory = memory
            self.model = model or ai_config.MODEL

            debug_log.debug(f"[AI_AGENT] Model: {self.model}, temp: {ai_config.TEMPERATURE}, streaming: {ai_config.STREAMING}")

            # Set global AppState reference for tools
            ai_tools.set_app_state(state)
            debug_log.debug(f"[AI_AGENT] AppState set for tools - {len(state.tasks)} tasks")

            # Initialize OpenAI LLM with streaming
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                debug_log.error("[AI_AGENT] OPENAI_API_KEY not found in environment!")
                raise ValueError("OPENAI_API_KEY not found. Please set it in .env file.")

            self.llm = ChatOpenAI(
                model=self.model,
                temperature=ai_config.TEMPERATURE,
                max_tokens=ai_config.MAX_TOKENS,
                streaming=ai_config.STREAMING,
                api_key=api_key
            )
            debug_log.debug("[AI_AGENT] ChatOpenAI LLM initialized")

            # Get all available tools
            self.tools = ai_tools.get_all_tools()
            debug_log.debug(f"[AI_AGENT] Registered {len(self.tools)} tools")

            # Create system prompt
            self.system_prompt = self._create_system_prompt()
            debug_log.debug(f"[AI_AGENT] System prompt created ({len(self.system_prompt)} chars)")

            # Create agent using new LangChain 1.0 API
            self.agent = create_agent(
                model=self.llm,
                tools=self.tools,
                system_prompt=self.system_prompt,
                debug=ai_config.AGENT_VERBOSE
            )
            debug_log.info(f"[AI_AGENT] Agent created successfully - model={self.model}, tools={len(self.tools)}")

        except Exception as e:
            debug_log.error(f"[AI_AGENT] Initialization failed: {str(e)}", exception=e)
            raise

    def ask(self, question: str, streaming_callback: Optional[Callable] = None) -> str:
        """
        Ask the AI assistant a question.

        Args:
            question: User's question or request
            streaming_callback: Optional callback for streaming (receives token strings)

        Returns:
            AI assistant's response

        Example:
            response = agent.ask("What are my high priority tasks?")
            response = agent.ask("Create a task for code review", streaming_callback=callback)
        """
        debug_log.debug(f"[AI_AGENT] ask() called - question: '{question[:50]}'")

        try:
            # Build context string from current app state
            context_info = self._build_context_string()
            debug_log.debug(f"[AI_AGENT] Context built - {len(context_info)} chars")

            # Get conversation history
            chat_context = self.memory.get_context_for_agent()
            history_text = self._format_chat_history(chat_context["chat_history"])
            debug_log.debug(f"[AI_AGENT] Chat history loaded - {len(chat_context['chat_history'])} messages")

            # Build full prompt with context
            full_prompt = f"""{context_info}

Previous conversation:
{history_text}

User question: {question}"""

            debug_log.debug(f"[AI_AGENT] Full prompt: {len(full_prompt)} chars")
            debug_log.info(f"[AI_AGENT] Invoking LangChain agent...")

            # Execute agent with new LangChain 1.0 API
            # The agent returns a dictionary with messages
            result = self.agent.invoke({"messages": [{"role": "user", "content": full_prompt}]})
            debug_log.debug(f"[AI_AGENT] Agent invoke completed - result keys: {list(result.keys()) if isinstance(result, dict) else 'not a dict'}")

            # Log tool calls if present
            if "messages" in result:
                for msg in result["messages"]:
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        for tool_call in msg.tool_calls:
                            tool_name = getattr(tool_call, "name", None) or tool_call.get("name", "unknown")
                            debug_log.info(f"[AI_AGENT] 🔧 Tool executed: {tool_name}")

            # Extract response from result
            # LangChain 1.0 returns messages in state
            if "messages" in result and result["messages"]:
                last_message = result["messages"][-1]
                response = last_message.content if hasattr(last_message, "content") else str(last_message)
                debug_log.debug(f"[AI_AGENT] Response extracted - {len(response)} chars")
            else:
                debug_log.error(f"[AI_AGENT] No messages in result - result type: {type(result)}")
                response = "No response generated"

            # Call streaming callback if provided (simulated streaming)
            if streaming_callback and response:
                debug_log.debug(f"[AI_AGENT] Calling streaming callback - {len(response)} chars")
                for char in response:
                    streaming_callback(char)

            # Save exchange to memory
            debug_log.debug("[AI_AGENT] Saving exchange to memory...")
            self.memory.add_exchange(question, response)
            debug_log.info(f"[AI_AGENT] ask() completed successfully - response: {len(response)} chars")

            return response

        except Exception as e:
            debug_log.error(f"[AI_AGENT] ask() failed: {str(e)}", exception=e)
            error_msg = f"Error: {str(e)}"
            # Still save error to memory for context
            try:
                self.memory.add_exchange(question, error_msg)
            except:
                pass  # Don't fail if memory save fails
            return f"❌ {error_msg}"

    def reset_conversation(self) -> None:
        """
        Clear conversation memory and start fresh.

        This wipes all conversation history and summaries.
        """
        debug_log.info("[AI_AGENT] Resetting conversation memory...")
        try:
            self.memory.clear()
            debug_log.info("[AI_AGENT] Conversation reset successfully")
        except Exception as e:
            debug_log.error(f"[AI_AGENT] Failed to reset conversation: {str(e)}", exception=e)
            raise

    def _build_context_string(self) -> str:
        """
        Build current state context string for agent prompt.

        Extracts information from AppState for inclusion in prompt.

        Returns:
            Formatted string with current workspace context
        """
        total = len(self.state.tasks)
        done = sum(1 for t in self.state.tasks if t.done)
        todo = total - done

        return f"""Current Workspace Context:
- Total tasks: {total}
- Done: {done} | Todo: {todo}
- Active filter: {self.state.filter}
- Current view: {self.state.view_mode}
- Page: {self.state.page + 1}"""

    def _format_chat_history(self, messages: list) -> str:
        """
        Format chat history for prompt injection.

        Args:
            messages: List of message dicts with 'role' and 'content'

        Returns:
            Formatted string of conversation history
        """
        if not messages:
            return "No previous conversation"

        formatted = []
        for msg in messages[-10:]:  # Only include last 10 messages
            role = msg["role"].capitalize()
            content = msg["content"][:200]  # Truncate long messages
            formatted.append(f"{role}: {content}")

        return "\n".join(formatted)

    def _create_system_prompt(self) -> str:
        """
        Create system prompt for the agent.

        The prompt includes:
        - Role description
        - Available tools description
        - Guidelines for responses

        Returns:
            System prompt string
        """
        return """You are an intelligent task management assistant with access to tools.

You have access to the following tools to help manage tasks:
1. **create_task** - Create new tasks with name, priority (1=HIGH, 2=MEDIUM, 3=LOW), tag, description, comment
2. **edit_task** - Modify existing task fields (name, priority, tag, description, comment)
3. **complete_task** - Mark tasks as done
4. **uncomplete_task** - Mark tasks as incomplete
5. **delete_task** - Delete tasks permanently
6. **search_tasks** - Find tasks by filter (done, undone, tag:NAME, priority=1/2/3)
7. **get_task_details** - View full details of a specific task
8. **get_task_statistics** - Get workspace summary and statistics

Guidelines:
- Be concise but helpful
- Use tools when appropriate to accomplish user requests
- Confirm actions taken (e.g., "Created task #5: Code review")
- Format responses with markdown for clarity
- If user asks to create/edit/complete/delete tasks, use the tools
- If user asks about tasks, use search_tasks or get_task_statistics
- For specific task details, use get_task_details
- Always provide task IDs when mentioning specific tasks

CRITICAL - Parameter Extraction Rules:
When creating or editing tasks, you MUST extract ALL information from user requests:

1. **Tags** - If user mentions multiple tags/categories/labels:
   - Use comma-separated format: tag="tag1,tag2,tag3"
   - Examples: "tags backend and api" → tag="backend,api"
   - Examples: "tags webasto, psdc, fa070" → tag="webasto,psdc,fa070"
   - NEVER use only the first tag - extract ALL of them

2. **Description vs Comment**:
   - description: Detailed technical requirements, specifications, acceptance criteria
   - comment: Short contextual notes, references, related information
   - If user provides detailed requirements/specs → use description parameter
   - If user provides quick notes/context → use comment parameter

3. **Priority Mapping**:
   - "high", "urgent", "critical", "important" → priority=1
   - "medium", "normal" → priority=2
   - "low", "minor" → priority=3

4. **Extract Everything**:
   - Read the ENTIRE user request carefully
   - Map each piece of information to the appropriate parameter
   - Don't leave fields empty if the user provided relevant information

Example Extractions:
- User: "create task FA070 send data - For each prism send results to LCS prio high - tags webasto, psdc, fa070"
  → create_task(name="FA070 send data", priority=1, tag="webasto,psdc,fa070", description="For each prism send results to LCS")

- User: "add task fix login bug on backend - related to issue #42 - urgent"
  → create_task(name="fix login bug on backend", priority=1, tag="backend", comment="Related to issue #42")"""
