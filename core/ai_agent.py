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
from core.state import LeftPanelMode
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

            # Collect unique tool calls (for UI hinting)
            # Deduplicate to avoid showing same tool multiple times
            tool_logs: list[str] = []
            seen_tools: set[str] = set()  # Track unique tool names

            if "messages" in result:
                for msg in result["messages"]:
                    # Only collect from AIMessage (not ToolMessage or other types)
                    # Check for 'type' attribute to filter message types
                    msg_type = getattr(msg, "type", None)
                    is_ai_message = msg_type == "ai" or (msg_type is None and hasattr(msg, "tool_calls"))

                    if is_ai_message and hasattr(msg, "tool_calls") and msg.tool_calls:
                        for tool_call in msg.tool_calls:
                            tool_name = getattr(tool_call, "name", None) or tool_call.get("name", "unknown")

                            # Only log each unique tool once
                            if tool_name not in seen_tools:
                                seen_tools.add(tool_name)
                                debug_log.info(f"[AI_AGENT] 🔧 Tool executed: {tool_name}")
                                tool_logs.append(f"[dim]> {tool_name}[/dim]")

            # Extract response from result
            # LangChain 1.0 returns messages in state
            if "messages" in result and result["messages"]:
                last_message = result["messages"][-1]
                response = last_message.content if hasattr(last_message, "content") else str(last_message)
                debug_log.debug(f"[AI_AGENT] Response extracted - {len(response)} chars")
            else:
                debug_log.error(f"[AI_AGENT] No messages in result - result type: {type(result)}")
                response = "No response generated"

            # Call streaming callback if provided (prelude with tool logs + simulated streaming)
            if streaming_callback and response:
                if tool_logs:
                    prelude = "\n".join(tool_logs) + "\n"
                    for ch in prelude:
                        streaming_callback(ch)
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
        Detects edit mode and highlights currently edited task/note.

        Returns:
            Formatted string with current workspace context
        """
        ctx = []

        # Check if user is editing a specific task or note
        panel_mode = getattr(self.state, 'left_panel_mode', None)
        selected_task_id = getattr(self.state, 'selected_task_id', None)
        selected_note_id = getattr(self.state, 'selected_note_id', None)
        is_new = getattr(self.state, 'edit_mode_is_new', False)

        # ===== CURRENT FOCUS (if editing) =====
        if panel_mode == LeftPanelMode.EDIT_TASK:
            if is_new:
                # CREATING NEW TASK - Special handling for task creation
                ctx.append("**CURRENT FOCUS** (You are CREATING a NEW task):")
                ctx.append("- Mode: Creating NEW task (not saved yet)")
                ctx.append("- User is filling in the task creation form")
                ctx.append("- Current state: Empty form, waiting for task details")
                ctx.append("")
                ctx.append("**Your role:**")
                ctx.append("- Help the user define and create the new task")
                ctx.append("- When ready, use create_task tool to save it")
                ctx.append("")
                ctx.append("**⚠️ CRITICAL RULE:**")
                ctx.append("- DO NOT use edit_task on ANY existing tasks")
                ctx.append("- The user is creating NEW, not editing existing")
                ctx.append("- If user says 'edit it' or 'change it', they mean the NEW task being created")
                ctx.append("")
                debug_log.info("[AI_AGENT] Context: User is CREATING NEW task")
            elif selected_task_id:
                # EDITING EXISTING TASK - Original logic
                ctx.append("**CURRENT FOCUS** (You are editing this task):")
                try:
                    task = next((t for t in self.state.tasks if t.id == selected_task_id), None)
                    if task:
                        ctx.append(f"- Task #{task.id}: \"{task.name}\"")
                        priority_label = {1: "HIGH", 2: "MEDIUM", 3: "LOW"}.get(task.priority, "UNKNOWN")
                        ctx.append(f"- Priority: {priority_label} ({task.priority})")
                        if task.tags:
                            ctx.append(f"- Tags: {', '.join(task.tags)}")
                        ctx.append(f"- Status: {'DONE' if task.done else 'UNDONE'}")
                        if task.comment:
                            ctx.append(f"- Comment: {task.comment}")
                        if task.description:
                            # Show first 200 chars of description
                            desc_preview = task.description[:200] + ("..." if len(task.description) > 200 else "")
                            ctx.append(f"- Description: {desc_preview}")
                        from utils.time import humanize_age
                        age = humanize_age(task.created_at) if task.created_at else "unknown"
                        ctx.append(f"- Created: {age}")
                        debug_log.info(f"[AI_AGENT] Context: User is EDITING task #{task.id}")
                    else:
                        ctx.append(f"- Task #{selected_task_id}: (not found)")
                except Exception as e:
                    debug_log.error(f"[AI_AGENT] Error building task focus context: {e}")
                    ctx.append(f"- Task #{selected_task_id}: (error loading details)")
                ctx.append("")  # Empty line separator

        elif panel_mode == LeftPanelMode.EDIT_NOTE and selected_note_id:
            ctx.append("**CURRENT FOCUS** (You are editing this note):")
            try:
                note = next((n for n in getattr(self.state, 'notes', []) if n.id.startswith(selected_note_id)), None)
                if note:
                    ctx.append(f"- Note {note.id[:8]}: \"{note.title}\"")
                    if note.tags:
                        ctx.append(f"- Tags: {', '.join(note.tags)}")
                    if note.task_ids:
                        ctx.append(f"- Linked to tasks: {', '.join(f'#{tid}' for tid in note.task_ids)}")
                    # Show first 300 chars of body
                    if note.body_md:
                        body_preview = note.body_md[:300] + ("..." if len(note.body_md) > 300 else "")
                        ctx.append(f"- Body excerpt: {body_preview}")
                    from utils.time import humanize_age
                    age = humanize_age(note.created_at) if note.created_at else "unknown"
                    ctx.append(f"- Created: {age}")
                    if is_new:
                        ctx.append("- Mode: Creating NEW note")
                else:
                    ctx.append(f"- Note {selected_note_id[:8]}: (not found)")
            except Exception as e:
                debug_log.error(f"[AI_AGENT] Error building note focus context: {e}")
                ctx.append(f"- Note {selected_note_id[:8]}: (error loading details)")
            ctx.append("")  # Empty line separator

        elif panel_mode == LeftPanelMode.DETAIL_TASK and selected_task_id:
            ctx.append("**CURRENT VIEW** (Viewing task detail):")
            try:
                task = next((t for t in self.state.tasks if t.id == selected_task_id), None)
                if task:
                    ctx.append(f"- Task #{task.id}: \"{task.name}\"")
                    priority_label = {1: "HIGH", 2: "MEDIUM", 3: "LOW"}.get(task.priority, "UNKNOWN")
                    ctx.append(f"- Priority: {priority_label}")
                    if task.tags:
                        ctx.append(f"- Tags: {', '.join(task.tags)}")
            except Exception:
                pass
            ctx.append("")

        elif panel_mode == LeftPanelMode.DETAIL_NOTE and selected_note_id:
            ctx.append("**CURRENT VIEW** (Viewing note detail):")
            try:
                note = next((n for n in getattr(self.state, 'notes', []) if n.id.startswith(selected_note_id)), None)
                if note:
                    ctx.append(f"- Note {note.id[:8]}: \"{note.title}\"")
                    if note.tags:
                        ctx.append(f"- Tags: {', '.join(note.tags)}")
            except Exception:
                pass
            ctx.append("")

        # ===== WORKSPACE SUMMARY =====
        total = len(self.state.tasks)
        done = sum(1 for t in self.state.tasks if t.done)
        todo = total - done
        notes_total = len(getattr(self.state, 'notes', [])) if hasattr(self.state, 'notes') else 0

        # Collect available tags for suggestions
        all_tags = set()
        for task in self.state.tasks:
            if task.tags:
                all_tags.update(task.tags)
        for note in getattr(self.state, 'notes', []):
            if note.tags:
                all_tags.update(note.tags)

        ctx.append("Workspace Summary:")
        ctx.append(f"- Total tasks: {total} ({done} done, {todo} undone)")
        ctx.append(f"- Total notes: {notes_total}")
        if all_tags:
            # Show top 10 most common tags
            tag_list = sorted(all_tags)[:10]
            ctx.append(f"- Available tags: {', '.join(tag_list)}{' (...)' if len(all_tags) > 10 else ''}")
        ctx.append(f"- Active filter: {self.state.filter}")
        ctx.append(f"- Current view: {self.state.view_mode}")

        return "\n".join(ctx)

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
        return """You are an intelligent task & notes assistant with access to tools.

You have access to the following tools to help manage tasks and notes:
1. **create_task** - Create new tasks with name, priority (1=HIGH, 2=MEDIUM, 3=LOW), tag, description, comment
2. **edit_task** - Modify existing task fields (name, priority, tag, description, comment)
3. **complete_task** - Mark tasks as done
4. **uncomplete_task** - Mark tasks as incomplete
5. **delete_task** - Delete tasks permanently
6. **search_tasks** - Find tasks by filter (done, undone, tag:NAME, priority=1/2/3)
7. **get_task_details** - View full details of a specific task
8. **get_task_statistics** - Get workspace summary and statistics
9. **get_current_edit_context** - Get full details of currently edited/viewed task or note (CONTEXT-AWARE)

Notes tools:
10. **create_note** - Create a new note (title, body_md, tags, task_ids)
11. **edit_note** - Edit a note (title, tags, body, add_task, remove_task) with optional mode=append for body
12. **link_note** / **unlink_note** - Link or unlink a note to/from a task
13. **delete_note** - Delete notes by id prefix (requires >=5 chars or force=True)
14. **search_notes** - Search notes by text, filter by task or tag
15. **get_note_details** - View note details with excerpt and links
16. **get_linked_notes_for_task** - List notes linked to a task

Guidelines:
- Be concise but helpful
- Use tools when appropriate to accomplish user requests
- Confirm actions taken (e.g., "Created task #5: Code review")
- Format responses with markdown for clarity
- If user asks to create/edit/complete/delete tasks, use the tools
- If user asks to save or retrieve longer text (meeting minutes, design decisions), prefer notes (create_note / edit_note) and link to relevant tasks
- If user asks about tasks, use search_tasks or get_task_statistics
- If user asks about notes, use search_notes or get_note_details
 - When editing note tags, you may accept "+tag" to add and "-tag" to remove; otherwise replace the tag list
- For specific task details, use get_task_details
- For specific note details, use get_note_details
- Always provide task IDs when mentioning specific tasks
 - Always provide note IDs (first 8 chars) when mentioning notes

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
   - For long content (minutes, in-depth writeups) use create_note/edit_note instead of comment
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
  → create_task(name="fix login bug on backend", priority=1, tag="backend", comment="Related to issue #42")

CONTEXT AWARENESS (CRITICAL):
When the user is editing a specific task or note, the workspace context will include a **CURRENT FOCUS** section with details about the item being edited.

TOOL USAGE BOUNDARIES (CRITICAL):
You MUST follow these rules to prevent data corruption:

1. **When CURRENT FOCUS shows "CREATING NEW task":**
   - The user is filling out a form for a NEW task (not editing existing)
   - Use create_task tool to save the task when ready
   - ⚠️ DO NOT use edit_task on ANY existing tasks
   - If user says "edit it", "change it", "update it" → they mean the NEW task being created, NOT an existing task
   - Example: User says "make it fancy" → Help design the new task, then call create_task

2. **When CURRENT FOCUS shows "EDITING Task #X":**
   - The user is editing a specific existing task (Task #X)
   - ONLY use edit_task with task_id=X (the exact task shown in CURRENT FOCUS)
   - ⚠️ DO NOT edit other tasks (even if user mentions them ambiguously)
   - The edit_task tool will BLOCK attempts to edit other tasks
   - If user wants to edit different task, tell them to navigate to that task first
   - Example: User editing Task #100 says "edit it" → Only edit Task #100, never Task #420

3. **When CURRENT FOCUS shows "EDITING Note" or "CREATING NEW note":**
   - Same rules apply as for tasks
   - Only modify the note shown in CURRENT FOCUS
   - Never edit other notes

4. **When NO CURRENT FOCUS (list view):**
   - User is browsing task/note list
   - You can use any tools on any tasks/notes freely
   - Can create, search, complete, delete tasks
   - Can help with workspace-wide queries

When you see CURRENT FOCUS in the context:
1. **Prioritize the current item** - Your primary focus should be on the task/note being edited
2. **Interpret references** - When user says "this task", "this note", "it", "the task", etc., they mean the CURRENT FOCUS item
3. **Suggest improvements** - Provide suggestions specific to the current item (better tags, priority, description improvements)
4. **Use existing tags** - When suggesting tags, prefer tags from the "Available tags" list to maintain consistency
5. **Stay focused** - Unless explicitly asked about other tasks/notes, keep responses focused on the current item
6. **Workspace context available** - You can still access all tasks/notes via tools if the user explicitly asks (e.g., "show all high priority tasks")

Examples:
- User CREATING NEW task says "make it fancy" → Help design new task, use create_task when ready
- User editing Task #42 says "suggest better tags" → Use edit_task(task_id=42, ...) ONLY
- User editing Task #100 says "edit task #420" → REFUSE with "You are editing Task #100, navigate to #420 first"
- User editing Note abc12345 says "is this clear?" → Analyze that note's content and provide feedback
- User editing Task #15 says "what other high priority tasks do I have?" → Use search_tasks(filter_expression="priority=1") to show all

When NOT in edit mode (no CURRENT FOCUS):
- Respond to workspace-wide queries normally
- Help create new items
- Provide summaries and statistics"""
