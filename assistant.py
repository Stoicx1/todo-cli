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


class Assistant:
    def __init__(self, model="gpt-4o-mini", state=None):
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.console = Console()

    def format_tasks(self, tasks):
        return "\n".join(
            f"[{t.id}] {t.name} | Priority: {t.priority} | Tag: {t.tag or 'none'} | Done: {t.done}\n"
            f"    Description: {t.description or '-'}\n"
            f"    Comment: {t.comment or '-'}"
            for t in tasks
        )

    def ask(self, tasks, user_prompt):
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
