# gpt_assistant.py

from dotenv import load_dotenv
from rich.console import Console
from rich.spinner import Spinner
from rich.live import Live
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

        # self.console.print("\n💬 [bold green]GPT Suggestion:[/bold green]\n")
        return response.choices[0].message.content
