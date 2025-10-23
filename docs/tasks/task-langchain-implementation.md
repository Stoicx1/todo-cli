# LangChain AI Agent Implementation

**Status:** In Progress
**Started:** 2025-10-22
**Goal:** Transform basic AI assistant into conversational agent with tool execution, persistent memory, and rich streaming

---

## Overview

Enhance the existing `?` command AI feature with:
- **LangChain Agent System** - AI can execute task operations (create, edit, complete, search)
- **Persistent Conversation Memory** - Remembers context across sessions
- **Rich Markdown Streaming** - Beautiful, formatted responses with live updates
- **Context Awareness** - Understands current filter, view mode, and state

---

## Architecture Design

### Component Structure

```
┌──────────────────────────────────────────────┐
│  CLI Application (main.py → app.py)         │
│                                              │
│  ┌────────────────────────────────────────┐ │
│  │ Enhanced ? Command (commands.py)       │ │
│  └────────────────┬───────────────────────┘ │
│                   │                          │
│  ┌────────────────▼───────────────────────┐ │
│  │ TaskAssistantAgent (ai_agent.py)       │ │
│  │  • ReAct agent (Reasoning + Acting)    │ │
│  │  • Tool orchestration                  │ │
│  │  • Context injection                   │ │
│  └───┬─────────────────────────┬──────────┘ │
│      │                         │             │
│  ┌───▼──────────┐   ┌──────────▼─────────┐  │
│  │ AI Tools     │   │ Memory Manager     │  │
│  │ (ai_tools.py)│   │ (conversation_     │  │
│  │              │   │  memory.py)        │  │
│  │ • create_task│   │ • Load/save JSON   │  │
│  │ • edit_task  │   │ • Auto-summarize   │  │
│  │ • search_tasks│  │ • Token tracking   │  │
│  │ • complete   │   └────────────────────┘  │
│  │ • get_details│                            │
│  │ • statistics │                            │
│  └──────┬───────┘                            │
│         │                                    │
│  ┌──────▼────────────────────────────────┐  │
│  │ AppState (state.py)                   │  │
│  │  • tasks list                         │  │
│  │  • Direct access (no API)             │  │
│  └───────────────────────────────────────┘  │
│                                              │
│  Files:                                      │
│  • tasks.json (task storage)                 │
│  • chat_history.json (conversation memory)   │
└──────────────────────────────────────────────┘
              ↕
    [OpenAI API] (external)
```

### Data Flow

**Example: "create a task for code review"**

```
1. User Input (main.py)
   ↓
2. Command Router (commands.py)
   - Detects "?" command
   - Extracts question text
   ↓
3. Agent (ai_agent.py)
   - Loads conversation memory
   - Builds context from AppState
   - Sends to OpenAI with tools
   ↓
4. OpenAI API
   - Reasons: "I need to create a task"
   - Returns: tool_call(create_task, {name: "code review"})
   ↓
5. Tool Execution (ai_tools.py)
   - create_task() runs locally
   - Accesses AppState directly
   - Saves to tasks.json
   - Returns: "✅ Created task #15"
   ↓
6. Agent Response
   - Receives tool result
   - Formats natural response
   - Streams tokens back
   ↓
7. Streaming Renderer (ai_renderer.py)
   - Displays markdown in real-time
   - Shows tool execution indicators
   - Rich formatting (panels, code blocks)
   ↓
8. Memory Save (conversation_memory.py)
   - Saves Q&A to chat_history.json
   - Auto-summarizes if needed
```

---

## Implementation Phases

### ✅ Phase 0: Planning & Documentation
- [x] Design architecture
- [x] Create implementation plan
- [x] Create this tracking document

### Phase 1: Setup & Dependencies
**Files:** `requirements.txt`, `config.py`

**Tasks:**
- [ ] Add LangChain dependencies to requirements.txt
  - `langchain>=0.1.0`
  - `langchain-openai>=0.0.5`
  - `langchain-community>=0.0.20`
- [ ] Add AI configuration section to config.py
  - Model settings (model, temperature)
  - Memory settings (max tokens, history limit)
  - Streaming configuration
  - File paths

**Estimated time:** 15 minutes

---

### Phase 2: AI Tools System
**File:** `core/ai_tools.py` (NEW - ~300 lines)

**Tools to implement:**

1. **create_task(name, priority=2, tag="", description="", comment="")**
   - Validates inputs
   - Creates Task object with next ID
   - Adds to AppState.tasks
   - Saves to tasks.json
   - Returns success message

2. **edit_task(task_id, field, value)**
   - Fields: name, priority, tag, description, comment, status
   - Validates field and value
   - Updates task in AppState
   - Saves changes
   - Returns confirmation

3. **complete_task(task_id)** / **uncomplete_task(task_id)**
   - Toggles task.done status
   - Updates completed timestamp
   - Saves and returns message

4. **search_tasks(filter_expression="none")**
   - Uses existing filter system
   - Returns formatted task list
   - Limits to 10 results (prevent token overflow)

5. **get_task_details(task_id)**
   - Returns full task information
   - Includes metadata (created, completed)
   - Formatted for AI consumption

6. **list_all_tags()**
   - Extracts unique tags from all tasks
   - Returns comma-separated list
   - Helps AI suggest relevant tags

7. **get_task_statistics()**
   - Returns task counts (total, done, todo)
   - Priority breakdown
   - Tag distribution
   - Active filter info

**Key points:**
- Each function decorated with `@tool` from LangChain
- Comprehensive docstrings (AI reads these!)
- Access AppState via singleton pattern
- Reuse existing validators (validate_priority, etc.)
- Return human-readable messages
- Error handling with helpful messages

**Estimated time:** 2 hours

---

### Phase 3: Conversation Memory System
**File:** `utils/conversation_memory.py` (NEW - ~200 lines)

**Class:** `ConversationMemoryManager`

**Methods:**
```python
__init__(memory_file="chat_history.json", max_token_limit=2000)
load_from_disk() -> None
save_to_disk() -> None
add_exchange(user_msg: str, ai_msg: str) -> None
get_history() -> dict
get_summary() -> str
clear() -> None
export_to_markdown(filename: str) -> None
get_stats() -> dict  # messages, tokens, has_summary
```

**Features:**
- Uses `ConversationSummaryBufferMemory` from LangChain
  - Keeps recent messages verbatim
  - Automatically summarizes old messages to save tokens
  - Token-aware (stays under limit)
- Persistent storage with file locking
  - Reuse `SafeFileManager` from existing system
  - JSON format: `{"messages": [...], "summary": "..."}`
- Cross-session memory
  - Load on startup
  - Save after each exchange

**Storage format (chat_history.json):**
```json
{
  "messages": [
    {"role": "user", "content": "create a task for X"},
    {"role": "assistant", "content": "✅ Created task #15"},
    {"role": "user", "content": "what tasks do I have?"},
    {"role": "assistant", "content": "You have 12 tasks..."}
  ],
  "summary": "User created a task for X. Discussed current task list...",
  "metadata": {
    "total_exchanges": 25,
    "last_updated": "2025-10-22T14:30:00"
  }
}
```

**Estimated time:** 1.5 hours

---

### Phase 4: AI Agent System
**File:** `core/ai_agent.py` (NEW - ~250 lines)

**Class:** `TaskAssistantAgent`

**Initialization:**
```python
def __init__(self, state: AppState, memory: ConversationMemoryManager, model="gpt-4o-mini"):
    self.state = state
    self.memory = memory

    # Initialize OpenAI with streaming
    self.llm = ChatOpenAI(
        model=model,
        temperature=0.7,
        streaming=True
    )

    # Register tools
    self.tools = [
        create_task,
        edit_task,
        complete_task,
        uncomplete_task,
        search_tasks,
        get_task_details,
        list_all_tags,
        get_task_statistics
    ]

    # Create agent with ReAct pattern
    self.agent = create_react_agent(self.llm, self.tools, self.prompt)
    self.executor = AgentExecutor(
        agent=self.agent,
        tools=self.tools,
        verbose=AGENT_VERBOSE,
        max_iterations=5,
        handle_parsing_errors=True
    )
```

**System Prompt Template:**
```
You are an intelligent task management assistant with access to tools.

Current Context:
- Total tasks: {task_count}
- Done: {done_count} | Todo: {todo_count}
- Active filter: {filter}
- Current view: {view_mode}
- Page: {page}

You can:
• Create new tasks with create_task(name, priority, tag, description)
• Edit existing tasks with edit_task(task_id, field, value)
• Mark tasks complete with complete_task(task_id)
• Search tasks with search_tasks(filter)
• Get detailed info with get_task_details(task_id)
• View statistics with get_task_statistics()

Guidelines:
- Be concise but helpful
- Use tools when appropriate
- Confirm actions taken
- Format responses with markdown

Conversation history:
{chat_history}

User question: {input}
```

**Methods:**
```python
ask(question: str, streaming_callback=None) -> str
    - Builds context from AppState
    - Loads conversation memory
    - Invokes agent with streaming
    - Saves exchange to memory
    - Returns response

_build_context() -> dict
    - Extracts current state info
    - Returns context dict for prompt

reset_conversation() -> None
    - Clears conversation memory
```

**Agent behavior (ReAct pattern):**
```
User: "create a high-priority task for database review"

Agent Reasoning:
Thought: I need to create a task with high priority.
Action: create_task
Action Input: {name: "database review", priority: 1}

Observation: ✅ Created task #15: database review (Priority: HIGH)

Thought: Task created successfully, I should confirm to user.
Final Answer: I've created a high-priority task (#15) for database review.
```

**Estimated time:** 2 hours

---

### Phase 5: Streaming Markdown Renderer
**File:** `ui/ai_renderer.py` (NEW - ~200 lines)

**Class 1: `StreamingMarkdownCallback`**
Extends `BaseCallbackHandler` from LangChain

```python
class StreamingMarkdownCallback(BaseCallbackHandler):
    def __init__(self, console: Console):
        self.console = console
        self.text = ""
        self.live = None

    def on_llm_start(self, *args, **kwargs):
        # Initialize Live display with panel
        self.text = ""
        self.live = Live(
            Panel(Markdown(""), title="🤖 AI Assistant", border_style="cyan"),
            console=self.console,
            refresh_per_second=10
        )
        self.live.start()

    def on_llm_new_token(self, token: str, **kwargs):
        # Append token and update display
        self.text += token
        self.live.update(
            Panel(Markdown(self.text), title="🤖 AI Assistant", border_style="cyan")
        )

    def on_llm_end(self, *args, **kwargs):
        # Stop live display
        if self.live:
            self.live.stop()

    def on_tool_start(self, serialized, input_str, **kwargs):
        # Show tool execution indicator
        tool_name = serialized.get("name", "unknown")
        self.console.print(f"[dim]Using tool: {tool_name}[/dim]")

    def on_tool_end(self, output, **kwargs):
        # Show tool result (optional)
        pass
```

**Class 2: `AIResponsePanel`**
Wrapper for formatted responses

```python
class AIResponsePanel:
    @staticmethod
    def render(content: str, title="🤖 AI Assistant"):
        return Panel(
            Markdown(content),
            title=title,
            border_style="cyan",
            padding=(1, 2)
        )
```

**Helper functions:**
```python
def render_thinking_indicator(console: Console):
    # Animated "AI is thinking..." spinner

def render_tool_execution(tool_name: str, console: Console):
    # Shows "[Using tool: create_task]"

def render_error(error_msg: str, console: Console):
    # Red error panel

def format_conversation_turn(turn: int, total: int) -> str:
    # Returns "Turn 5/20" for display
```

**Markdown support:**
- Headers (# ## ###)
- Lists (bullets, numbered)
- Code blocks with syntax highlighting
- Tables
- Bold/italic
- Links

**Estimated time:** 1.5 hours

---

### Phase 6: Enhanced ? Command Integration
**File:** `core/commands.py` (MODIFY)

**Current code (lines ~689-698):**
```python
elif cmd == "?":
    if not state.tasks:
        state.messages.append("[!] No tasks to analyze.")
        return

    user_prompt = Prompt.ask(
        "🤖 GPT Prompt", default="Which tasks should I prioritize today?"
    )
    gpt.console = console
    state.messages.append(dedent(gpt.ask(state.tasks, user_prompt)))
```

**New implementation:**
```python
elif cmd == "?":
    # Subcommands for memory management
    if len(parts) > 1:
        subcmd = parts[1]

        if subcmd == "clear":
            # Clear conversation history
            gpt.agent.reset_conversation()
            state.messages.append("[green]✅ Conversation history cleared[/green]")
            return

        elif subcmd == "export":
            # Export chat to markdown
            filename = parts[2] if len(parts) > 2 else "chat_export.md"
            gpt.agent.memory.export_to_markdown(filename)
            state.messages.append(f"[green]✅ Conversation exported to {filename}[/green]")
            return

        elif subcmd == "memory":
            # Show memory statistics
            stats = gpt.agent.memory.get_stats()
            state.messages.append(
                f"💾 Memory Stats:\n"
                f"   Messages: {stats['messages']}\n"
                f"   Tokens: ~{stats['tokens']}\n"
                f"   Summary: {'Yes' if stats['has_summary'] else 'No'}"
            )
            return

        elif subcmd == "reset":
            # Reset conversation and confirm
            if confirm("Reset conversation and start fresh?", default=False):
                gpt.agent.reset_conversation()
                state.messages.append("[green]✅ Conversation reset[/green]")
            return

    # Extract question (inline or prompt)
    question = " ".join(parts[1:]) if len(parts) > 1 else ""

    if not question:
        question = Prompt.ask(
            "🤖 Ask AI",
            default="What should I work on today?"
        )

    # Create streaming callback
    from ui.ai_renderer import StreamingMarkdownCallback
    callback = StreamingMarkdownCallback(console)

    # Ask agent (with streaming)
    try:
        response = gpt.ask(question, streaming_callback=callback)
        # Response already displayed via streaming callback
        # Optionally add to messages for reference
        state.messages.append(f"[dim]Last AI response saved to history[/dim]")

    except Exception as e:
        state.messages.append(f"[red]❌ AI Error: {str(e)}[/red]")
```

**New usage patterns:**
```bash
# Inline question
❯ ? what tasks are urgent

# Prompted question
❯ ?
🤖 Ask AI: create a task for code review

# Subcommands
❯ ? clear           # Clear conversation history
❯ ? export          # Export to chat_export.md
❯ ? export log.md   # Export to specific file
❯ ? memory          # Show memory stats
❯ ? reset           # Start fresh conversation
```

**Estimated time:** 1 hour

---

### Phase 7: Assistant Integration
**File:** `assistant.py` (MODIFY)

**Current code:**
```python
class Assistant:
    def __init__(self, model="gpt-4o-mini", state=None):
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.console = Console()

    def format_tasks(self, tasks):
        # ...

    def ask(self, tasks, user_prompt):
        # Simple API call
```

**New code:**
```python
from core.ai_agent import TaskAssistantAgent
from utils.conversation_memory import ConversationMemoryManager
from config import CHAT_HISTORY_FILE, MEMORY_MAX_TOKENS

class Assistant:
    def __init__(self, model="gpt-4o-mini", state=None):
        load_dotenv()
        self.state = state
        self.console = Console()

        # Initialize conversation memory
        self.memory = ConversationMemoryManager(
            memory_file=CHAT_HISTORY_FILE,
            max_token_limit=MEMORY_MAX_TOKENS
        )

        # Initialize agent with tools
        self.agent = TaskAssistantAgent(
            state=state,
            memory=self.memory,
            model=model
        )

    def ask(self, user_prompt, streaming_callback=None):
        """
        Ask AI a question (new signature - no tasks param needed)
        Agent accesses state directly via tools
        """
        return self.agent.ask(user_prompt, streaming_callback)

    # Keep old methods for backward compatibility if needed
    def format_tasks(self, tasks):
        return "\n".join(
            f"[{t.id}] {t.name} | Priority: {t.priority} | Tag: {t.tag or 'none'} | Done: {t.done}"
            for t in tasks
        )
```

**Key changes:**
- Agent initialization in `__init__`
- Memory management added
- `ask()` method simplified (agent handles everything)
- No longer needs task list parameter (tools access state)

**Estimated time:** 30 minutes

---

### Phase 8: Configuration
**File:** `config.py` (ADD section)

**New configuration section:**
```python
# ============================================
# AI Assistant Configuration
# ============================================

# OpenAI Model Settings
AI_MODEL = "gpt-4o-mini"
AI_TEMPERATURE = 0.7
AI_MAX_TOKENS = 1500
AI_STREAMING = True

# Conversation Memory Settings
CHAT_HISTORY_FILE = "chat_history.json"
MEMORY_MAX_TOKENS = 2000  # Keep ~2000 tokens in memory
MEMORY_MAX_MESSAGES = 50  # Max messages before forced summarization

# Agent Settings
AGENT_VERBOSE = False  # Set True to see reasoning steps (debugging)
AGENT_MAX_ITERATIONS = 5  # Prevent infinite loops
AGENT_HANDLE_PARSING_ERRORS = True  # Graceful error recovery

# Tool Execution Settings
TOOL_SEARCH_LIMIT = 10  # Max tasks returned by search_tasks
TOOL_REQUIRE_CONFIRMATION = False  # Set True for destructive operations
```

**Estimated time:** 10 minutes

---

### Phase 9: Testing
**Test scenarios:**

1. **Basic conversation**
   ```bash
   ❯ ? what tasks do I have?
   Expected: Uses search_tasks tool, returns formatted list
   ```

2. **Task creation from prompt**
   ```bash
   ❯ ? create a high-priority task for database review tagged as backend
   Expected: Uses create_task tool, confirms creation with task ID
   ```

3. **Task editing**
   ```bash
   ❯ ? change task 5 to medium priority
   Expected: Uses edit_task tool, confirms update
   ```

4. **Multi-turn conversation**
   ```bash
   ❯ ? what are my urgent tasks?
   [AI responds with list]
   ❯ ? mark task 8 as done
   Expected: Remembers context, completes task 8
   ```

5. **Memory persistence**
   ```bash
   ❯ ? create a task for code review
   [Exit CLI]
   [Restart CLI]
   ❯ ? what did we just talk about?
   Expected: Remembers task creation
   ```

6. **Streaming display**
   ```bash
   ❯ ? analyze my workload
   Expected: See response word-by-word with markdown formatting
   ```

7. **Error handling**
   ```bash
   ❯ ? mark task 999 as done
   Expected: Graceful error, "Task 999 not found"
   ```

8. **Memory management**
   ```bash
   ❯ ? memory
   Expected: Shows message count, token usage

   ❯ ? clear
   Expected: Clears history, confirms
   ```

9. **Tool execution visibility**
   ```bash
   ❯ ? create 3 tasks for: design, code, test
   Expected: Shows "Using tool: create_task" indicators
   ```

10. **Complex multi-tool queries**
    ```bash
    ❯ ? find my backend tasks, mark task 5 as done, and tell me what's left
    Expected: Uses search_tasks, complete_task, formats results
    ```

**Estimated time:** 1 hour

---

### Phase 10: Documentation
**File:** `CLAUDE.md` (UPDATE)

Add new section:

```markdown
### AI Assistant with LangChain Agents (NEW - 2025-10-22)

The application now features an intelligent AI assistant powered by LangChain agents with tool execution capabilities.

**Architecture:**
- **Agent System** (`core/ai_agent.py`) - ReAct agent with OpenAI
- **Tools** (`core/ai_tools.py`) - 7 tools for task operations
- **Memory** (`utils/conversation_memory.py`) - Persistent conversation with auto-summarization
- **Renderer** (`ui/ai_renderer.py`) - Streaming markdown display

**Capabilities:**
- Create tasks from natural language
- Edit existing tasks
- Search with advanced filters
- Complete/uncomplete tasks
- Get task details and statistics
- Remembers conversation across sessions
- Streams responses in real-time

**Usage:**
```bash
# Ask questions
❯ ? what are my urgent tasks

# Create tasks
❯ ? create a high-priority task for code review

# Edit tasks
❯ ? change task 5 to medium priority

# Complex operations
❯ ? find backend tasks and mark task 8 as done

# Memory management
❯ ? clear           # Clear conversation
❯ ? export          # Export to markdown
❯ ? memory          # Show stats
```

**How it works:**
1. User asks question via `?` command
2. Agent analyzes question and decides which tools to use
3. Tools execute locally (direct AppState access)
4. Response streams back with markdown formatting
5. Conversation saved to `chat_history.json`

**Memory Management:**
- Keeps recent messages verbatim
- Auto-summarizes old messages to save tokens
- Persists across sessions
- Token-aware (stays under 2000 token limit)

**Configuration:** See `config.py` for AI settings
```

**Estimated time:** 30 minutes

---

## Technical Decisions

### Why LangChain?
- **Agent framework** - ReAct pattern for tool orchestration
- **Memory management** - Smart summarization and token tracking
- **Extensibility** - Easy to add new tools
- **Production-ready** - Battle-tested by thousands of apps

### Why ReAct Agent?
- **Transparent reasoning** - Shows thought process (optional)
- **Multi-step planning** - Can chain multiple tools
- **Error recovery** - Handles failed tool calls gracefully

### Why JSON Memory?
- **Simple** - No database required
- **Portable** - Easy to backup/export
- **Compatible** - Reuses existing file safety system
- **Human-readable** - Can inspect/edit manually

### Why Streaming?
- **Better UX** - See response as it generates
- **Engagement** - Feels more interactive
- **Feedback** - Shows progress for long responses

---

## Future Enhancements

### Short-term (v2)
- [ ] Confirmation prompts for destructive operations
- [ ] Bulk operations ("create 5 tasks for...")
- [ ] Task templates ("create sprint tasks")
- [ ] Smart suggestions ("you haven't worked on X in a while")

### Medium-term (v3)
- [ ] Multi-agent system (planner + executor)
- [ ] RAG for task history search
- [ ] Voice input integration
- [ ] Scheduled AI reviews (daily summaries)

### Long-term (v4)
- [ ] GitHub integration (create tasks from issues)
- [ ] Notion/Trello sync
- [ ] Team collaboration features
- [ ] Analytics dashboard

---

## Dependencies

### New packages:
```
langchain>=0.1.0              # Core framework
langchain-openai>=0.0.5       # OpenAI integration
langchain-community>=0.0.20   # Community tools
```

### Transitive dependencies (~8 packages):
- `pydantic` - Data validation
- `langsmith` - Observability (optional)
- `tenacity` - Retry logic
- Others from LangChain ecosystem

---

## Performance Considerations

### Token Usage
- **Memory limit:** 2000 tokens (~1500 words)
- **Auto-summarization:** Old messages compressed to ~200 tokens
- **Cost per exchange:** ~$0.001-0.003 (gpt-4o-mini)

### Latency
- **Agent thinking:** 1-3 seconds
- **Tool execution:** <100ms (local)
- **Streaming start:** ~500ms
- **Total response:** 2-5 seconds

### Storage
- **chat_history.json:** ~1-5 KB per session
- **Growth:** ~10 KB per 100 exchanges
- **Cleanup:** Manual or automated rotation

---

## Troubleshooting

### Agent not using tools
- Check `AGENT_VERBOSE=True` in config to see reasoning
- Verify tool docstrings are descriptive
- Ensure OpenAI API key is valid

### Memory not persisting
- Check `chat_history.json` file permissions
- Verify `SafeFileManager` is working
- Check for file lock errors

### Streaming not working
- Verify `AI_STREAMING=True` in config
- Check console supports live updates
- Try without streaming (set to False)

### Token limit exceeded
- Reduce `MEMORY_MAX_TOKENS` in config
- Clear history more frequently
- Use more aggressive summarization

---

## Progress Tracking

### Completed
- [x] Architecture design
- [x] Implementation plan
- [x] Documentation structure

### In Progress
- [ ] Phase 1: Setup
- [ ] Phase 2: Tools
- [ ] Phase 3: Memory
- [ ] Phase 4: Agent
- [ ] Phase 5: Renderer
- [ ] Phase 6: Command integration
- [ ] Phase 7: Assistant update
- [ ] Phase 8: Configuration
- [ ] Phase 9: Testing
- [ ] Phase 10: Documentation

### Next Steps
1. Add dependencies to requirements.txt
2. Create config section
3. Implement ai_tools.py
4. Continue with remaining phases

---

## Notes

- Keep existing `?` command syntax for backward compatibility
- Maintain file safety system for chat_history.json
- Reuse existing validators and utilities
- Windows compatibility (encoding, emojis)
- Graceful fallback if OpenAI API unavailable

---

**Last Updated:** 2025-10-22
**Implementation Status:** Phase 0 complete, ready for Phase 1
