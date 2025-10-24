# gpt_assistant.py

from dotenv import load_dotenv
from rich.console import Console
from rich.spinner import Spinner
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from openai import OpenAI
import os
import json

# New LangChain agent imports
from core.ai_agent import TaskAssistantAgent
from utils.conversation_memory import ConversationMemoryManager
from config import ai as ai_config
from debug_logger import debug_log


class Assistant:
    def __init__(self, model="gpt-4o-mini", state=None):
        load_dotenv()
        self.state = state
        self.console = Console()

        # Legacy OpenAI client (kept for backward compatibility)
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=api_key)
        self.model = model

        # New LangChain agent system
        debug_log.info("[ASSISTANT] Attempting to initialize LangChain agent...")
        try:
            # Initialize conversation memory
            self.memory = ConversationMemoryManager(
                memory_file=ai_config.CHAT_HISTORY_FILE,
                max_token_limit=ai_config.MEMORY_MAX_TOKENS
            )
            debug_log.debug("[ASSISTANT] ConversationMemoryManager initialized")

            # Initialize agent with tools
            self.agent = TaskAssistantAgent(
                state=state,
                memory=self.memory,
                model=model
            )
            debug_log.info(f"[ASSISTANT] Agent initialized successfully - model={model}")

            self.agent_enabled = True
        except Exception as e:
            # Fallback to legacy mode if agent initialization fails
            debug_log.error(f"[ASSISTANT] Agent initialization failed, falling back to legacy mode: {str(e)}", exception=e)
            print(f"Warning: Agent initialization failed, using legacy mode: {e}")
            self.agent_enabled = False
            self.agent = None
            self.memory = None

    def format_tasks(self, tasks):
        return "\n".join(
            f"[{t.id}] {t.name} | Priority: {t.priority} | Tag: {t.tag or 'none'} | Done: {t.done}\n"
            f"    Description: {t.description or '-'}\n"
            f"    Comment: {t.comment or '-'}"
            for t in tasks
        )

    def ask(self, user_prompt, streaming_callback=None):
        """
        Ask AI a question (new signature with agent system).

        Args:
            user_prompt: User's question or request
            streaming_callback: Optional callback for streaming responses

        Returns:
            AI response text

        Note: If agent is enabled, uses LangChain agent with tools.
              Otherwise, falls back to legacy OpenAI API.
        """
        debug_log.debug(f"[ASSISTANT] ask() called - agent_enabled={self.agent_enabled}, prompt: '{user_prompt[:50]}'")

        if self.agent_enabled and self.agent:
            # Use new agent system
            debug_log.info("[ASSISTANT] Routing to LangChain agent")
            try:
                result = self.agent.ask(user_prompt, streaming_callback=streaming_callback)
                debug_log.debug(f"[ASSISTANT] Agent returned response - {len(result)} chars")
                return result
            except Exception as e:
                # Fallback to legacy on error
                debug_log.error(f"[ASSISTANT] Agent failed, falling back to legacy: {str(e)}", exception=e)
                print(f"Agent error, falling back to legacy: {e}")
                return self._ask_legacy(self.state.tasks, user_prompt)
        else:
            # Use legacy method
            debug_log.info("[ASSISTANT] Routing to legacy OpenAI API")
            return self._ask_legacy(self.state.tasks, user_prompt)

    def _ask_legacy(self, tasks, user_prompt):
        formatted_tasks = self.format_tasks(tasks)
        full_prompt = f"""
Here is my current task list:
{formatted_tasks}

{user_prompt}
        """

        with Live(Spinner("dots", text="Thinking..."), refresh_per_second=10):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant for managing tasks.",
                    },
                    {"role": "user", "content": full_prompt},
                ],
                temperature=0.7,
            )

        # self.console.print("\ndY'� [bold green]GPT Suggestion:[/bold green]\n")
        return response.choices[0].message.content

    def stream_chunks(self, tasks, user_prompt):
        """
        Yield content chunks from the streaming completion.

        This is a thin generator over the OpenAI chat.completions stream
        to be used by the app for non-blocking UI updates.
        """
        formatted_tasks = self.format_tasks(tasks)
        full_prompt = f"""
Here is my current task list:
{formatted_tasks}

{user_prompt}
        """

        stream = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant for managing tasks.",
                },
                {"role": "user", "content": full_prompt},
            ],
            temperature=0.7,
            stream=True,
        )

        for chunk in stream:
            try:
                delta = chunk.choices[0].delta.content or ""
            except Exception:
                delta = getattr(getattr(chunk.choices[0], "delta", object()), "content", "") or ""
            if delta:
                yield delta

    def ask_stream(self, tasks, user_prompt, console: Console, tail_lines: int = 20):
        """
        Stream the assistant response while always showing the latest tail_lines
        at the bottom. Returns the full final text when complete.

        Args:
            tasks: List of Task objects to include as context
            user_prompt: The user's question/prompt
            console: Rich Console to render the live view
            tail_lines: Number of last lines to keep visible during streaming
        """
        formatted_tasks = self.format_tasks(tasks)
        full_prompt = f"""
Here is my current task list:
{formatted_tasks}

{user_prompt}
        """

        buffer = ""
        title = "GPT Answer (streaming)"

        # Live tail view during streaming
        with Live(Panel("Thinking...", title=title, border_style="cyan"), refresh_per_second=10, console=console) as live:
            try:
                stream = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a helpful assistant for managing tasks.",
                        },
                        {"role": "user", "content": full_prompt},
                    ],
                    temperature=0.7,
                    stream=True,
                )

                for chunk in stream:
                    try:
                        delta = chunk.choices[0].delta.content or ""
                    except Exception:
                        # Some SDK variants use different attributes; be defensive
                        delta = getattr(getattr(chunk.choices[0], "delta", object()), "content", "") or ""

                    if not delta:
                        continue
                    buffer += delta

                    # Update live panel with the last tail_lines
                    lines = buffer.splitlines()
                    tail_text = "\n".join(lines[-tail_lines:]) if lines else ""
                    live.update(Panel(tail_text, title=title, border_style="cyan"))

            except Exception as e:
                # Show error and return what we have
                live.update(Panel(f"[red]Error:[/red] {e}", title=title, border_style="red"))

        return buffer.strip()

    def stream_with_context(self, tasks, user_prompt, conversation_context=None):
        """
        Stream GPT response with conversation context (context-aware chat)

        Args:
            tasks: List of Task objects to include as context
            user_prompt: The user's new question/prompt
            conversation_context: List of previous messages in OpenAI format
                                 [{"role": "user"|"assistant", "content": "..."}]

        Yields:
            String chunks from the streaming response
        """
        formatted_tasks = self.format_tasks(tasks)

        # Build messages array with context
        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant for managing tasks. "
                          "You have access to the user's current task list and can provide "
                          "advice, prioritization, analysis, and suggestions."
            }
        ]

        # Add conversation history if provided
        if conversation_context:
            messages.extend(conversation_context)

        # Add current task context + user prompt
        context_prompt = f"""
Here is my current task list:
{formatted_tasks}

{user_prompt}
"""
        messages.append({"role": "user", "content": context_prompt})

        # Stream the response
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
            stream=True,
        )

        for chunk in stream:
            try:
                delta = chunk.choices[0].delta.content or ""
            except Exception:
                delta = getattr(getattr(chunk.choices[0], "delta", object()), "content", "") or ""
            if delta:
                yield delta
