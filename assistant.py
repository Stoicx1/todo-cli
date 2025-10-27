"""
Lightweight Assistant for Textual UI (no Rich dependency).

Provides a simple ask() API with optional streaming via OpenAI when
OPENAI_API_KEY is configured. Falls back to a deterministic local message
when OpenAI is not available.
"""

from __future__ import annotations

import os
try:
    from dotenv import load_dotenv  # type: ignore
except Exception:
    load_dotenv = None  # type: ignore
from typing import Callable, Optional, Any
from config import ai as ai_config
from debug_logger import debug_log


class Assistant:
    def __init__(self, state: Any | None = None):
        self.state = state
        self._client = None
        self.agent = None
        self.agent_enabled = False
        self.memory = None

        # Load .env if available
        try:
            if load_dotenv is not None:
                load_dotenv()
                debug_log.debug("[ASSISTANT] Loaded .env for environment variables")
        except Exception as e:
            debug_log.warning(f"[ASSISTANT] Failed to load .env: {e}")

        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key:
            # Initialize LangChain agent (preferred - has tool calling)
            debug_log.info("[ASSISTANT] Attempting to initialize LangChain agent...")
            try:
                from core.ai_agent import TaskAssistantAgent
                from utils.conversation_memory import ConversationMemoryManager

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
                    model=ai_config.MODEL
                )
                self.agent_enabled = True
                debug_log.info(f"[ASSISTANT] LangChain agent initialized successfully - model={ai_config.MODEL}")
            except Exception as e:
                debug_log.error(f"[ASSISTANT] LangChain agent init failed, will use fallback: {e}", exception=e)
                self.agent_enabled = False
                self.agent = None
                self.memory = None

            # Initialize basic OpenAI client (fallback)
            try:
                from openai import OpenAI  # type: ignore
                self._client = OpenAI()
                debug_log.info("[ASSISTANT] OpenAI client initialized (fallback)")
            except Exception as e:
                debug_log.warning(f"[ASSISTANT] OpenAI init failed: {e}")
                self._client = None
        else:
            debug_log.info("[ASSISTANT] OPENAI_API_KEY not set; using local fallback")

    def ask(self, prompt: str, streaming_callback: Optional[Callable[[str], None]] = None) -> str:
        """Ask the assistant a question. Streams tokens when possible.

        Args:
            prompt: User prompt/question
            streaming_callback: Optional callable receiving incremental text tokens

        Returns:
            Final response text
        """
        # Priority 1: Try LangChain agent (has full tool calling capabilities)
        if self.agent_enabled and self.agent:
            debug_log.info("[ASSISTANT] Routing to LangChain agent")
            try:
                result = self.agent.ask(prompt, streaming_callback=streaming_callback)
                debug_log.debug(f"[ASSISTANT] Agent returned response - {len(result)} chars")
                return result
            except Exception as e:
                debug_log.error(f"[ASSISTANT] Agent failed, falling back: {e}", exception=e)
                # Continue to fallbacks below

        # Priority 2: Try simple tool routing (emergency fallback, no LangChain)
        try:
            tool_result = self._maybe_handle_tools(prompt, streaming_callback)
            if tool_result is not None:
                debug_log.info("[ASSISTANT] Simple tool routing handled request")
                return tool_result
        except Exception as e:
            debug_log.warning(f"[ASSISTANT] Simple tool routing failed: {e}")

        # Priority 3: OpenAI basic chat (no tools)
        if self._client is not None:
            model = getattr(ai_config, "MODEL", "gpt-4o-mini")
            try:
                # Try Chat Completions streaming first for compatibility
                try:
                    stream = self._client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        stream=True,
                        temperature=getattr(ai_config, "TEMPERATURE", 0.7),
                        max_tokens=getattr(ai_config, "MAX_TOKENS", 1500),
                    )
                    full = []
                    for chunk in stream:  # type: ignore[attr-defined]
                        try:
                            delta = chunk.choices[0].delta.content or ""
                        except Exception:
                            delta = ""
                        if delta:
                            full.append(delta)
                            if streaming_callback:
                                try:
                                    streaming_callback(delta)
                                except Exception:
                                    pass
                    return "".join(full)
                except Exception:
                    # Fallback to non-streaming completion
                    resp = self._client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=getattr(ai_config, "TEMPERATURE", 0.7),
                        max_tokens=getattr(ai_config, "MAX_TOKENS", 1500),
                        stream=False,
                    )
                    text = (resp.choices[0].message.content or "").strip()
                    if text and streaming_callback:
                        try:
                            streaming_callback(text)
                        except Exception:
                            pass
                    return text
            except Exception as e:
                debug_log.error(f"[ASSISTANT] OpenAI request failed: {e}", exception=e)

        # Local fallback response (deterministic, no network, streams once)
        fallback = (
            "AI is not configured. Set OPENAI_API_KEY to enable real responses.\n"
            "Prompt received: " + prompt[:200]
        )
        if streaming_callback:
            try:
                streaming_callback(fallback)
            except Exception:
                pass
        return fallback

    def _maybe_handle_tools(self, prompt: str, streaming_callback: Optional[Callable[[str], None]] = None) -> Optional[str]:
        """Handle common task/note intents directly without LangChain.

        Supports now:
          - create/add/new task (title, priority, tags)
          - done/undone/remove <id>
          - show/details <id>
          - search/find/filter tasks <expr>
          - stats/statistics/summary (tasks)
          - notes: create/new note, search/find notes, delete note <id>,
            link/unlink note <id> to task <n>, note details <id>,
            convert note <id> to task [priority/tags], append note <id> to task <n>
        """
        import re
        text = (prompt or "").strip()
        p = text.lower()
        if not p:
            return None

        try:
            from core import ai_tools
            if self.state is not None:
                try:
                    ai_tools.set_app_state(self.state)
                except Exception:
                    pass

            # ---- Done / Undone / Remove ----
            m = re.search(r"\b(done|complete)\s+(\d+)\b", p)
            if m:
                tid = int(m.group(2))
                res = ai_tools.complete_task(task_id=tid)
                if streaming_callback:
                    streaming_callback(res)
                return res
            m = re.search(r"\b(undone|uncomplete|reopen)\s+(\d+)\b", p)
            if m:
                tid = int(m.group(2))
                res = ai_tools.uncomplete_task(task_id=tid)
                if streaming_callback:
                    streaming_callback(res)
                return res
            m = re.search(r"\b(remove|delete|del)\s+(\d+)\b", p)
            if m:
                tid = int(m.group(2))
                res = ai_tools.delete_task(task_id=tid)
                if streaming_callback:
                    streaming_callback(res)
                return res

            # ---- Show details / search / stats ----
            m = re.search(r"\b(show|details?)\s+(\d+)\b", p)
            if m:
                tid = int(m.group(2))
                res = ai_tools.get_task_details(task_id=tid)
                if streaming_callback:
                    streaming_callback(res)
                return res
            if re.search(r"\b(stats|statistics|summary)\b", p):
                res = ai_tools.get_task_statistics()
                if streaming_callback:
                    streaming_callback(res)
                return res
            m = re.search(r"\b(search|find|filter)\s+tasks?\s+(.+)$", p)
            if m:
                expr = (m.group(2) or "none").strip()
                res = ai_tools.search_tasks(filter_expression=expr)
                if streaming_callback:
                    streaming_callback(res)
                return res

            # ---- Notes operations ----
            # link note <id> to task <n>
            m = re.search(r"\blink\s+note\s+([a-z0-9-]{4,})\s+to\s+task\s+(\d+)\b", p)
            if m:
                nid, tid = m.group(1), int(m.group(2))
                res = ai_tools.link_note(note_id=nid, task_id=tid)
                if streaming_callback:
                    streaming_callback(res)
                return res
            # unlink note <id> from task <n>
            m = re.search(r"\bunlink\s+note\s+([a-z0-9-]{4,})\s+(from|and)?\s*task\s+(\d+)\b", p)
            if m:
                nid, tid = m.group(1), int(m.group(3))
                res = ai_tools.unlink_note(note_id=nid, task_id=tid)
                if streaming_callback:
                    streaming_callback(res)
                return res
            # delete note <id>
            m = re.search(r"\b(delete|remove)\s+note\s+([a-z0-9-]{3,})\b", p)
            if m:
                nid = m.group(2)
                res = ai_tools.delete_note(note_id_prefix=nid, force=True)
                if streaming_callback:
                    streaming_callback(res)
                return res
            # note details <id>
            m = re.search(r"\b(note\s+details|show\s+note)\s+([a-z0-9-]{4,})\b", p)
            if m:
                nid = m.group(2)
                res = ai_tools.get_note_details(note_id=nid)
                if streaming_callback:
                    streaming_callback(res)
                return res
            # search notes ...
            m = re.search(r"\b(search|find)\s+notes?\s+(.+)$", p)
            if m:
                q = (m.group(2) or "").strip()
                res = ai_tools.search_notes(query=q)
                if streaming_callback:
                    streaming_callback(res)
                return res
            # create note "Title" [tags ...] [task N]
            if re.search(r"\b(create|new|add)\s+note\b", p):
                title = ""
                mm = re.search(r'"([^"]+)"|\'([^\']+)\'', text)
                if mm:
                    title = mm.group(1) or mm.group(2) or "New Note"
                else:
                    # crude: take after 'note'
                    parts = text.split("note", 1)
                    title = parts[1].strip().strip(':').strip() if len(parts) > 1 else "New Note"
                # tags
                tags_str = ""
                tm = re.search(r"tags?\s*(=|:)?\s+(.+)$", text, flags=re.IGNORECASE)
                if tm:
                    tags_str = tm.group(2).strip()
                    for sep in [".", "\n"]:
                        cut = tags_str.find(sep)
                        if cut != -1:
                            tags_str = tags_str[:cut]
                    tags = [t.strip() for t in re.split(r"[,\s]+", tags_str) if t.strip()]
                    tags_str = ",".join(tags)
                # task link
                link_task_id = None
                lm = re.search(r"\btask\s+(\d+)\b", p)
                if lm:
                    link_task_id = int(lm.group(1))
                # create
                res = ai_tools.create_note(title=title, body_md="", tags=tags_str, task_ids=str(link_task_id or ""))
                if streaming_callback:
                    streaming_callback(res)
                return res
            # convert note <id> to task [priority/tags]
            m = re.search(r"\bconvert\s+note\s+([a-z0-9-]{4,})\s+to\s+task\b", p)
            if m:
                nid = m.group(1)
                prio = 2
                if re.search(r"priority\s*(=|:)?\s*1|priority\s*high", p):
                    prio = 1
                elif re.search(r"priority\s*(=|:)?\s*3|priority\s*low", p):
                    prio = 3
                tags_str = ""
                tm = re.search(r"tags?\s*(=|:)?\s+(.+)$", text, flags=re.IGNORECASE)
                if tm:
                    raw = tm.group(2).strip()
                    for sep in [".", "\n"]:
                        cut = raw.find(sep)
                        if cut != -1:
                            raw = raw[:cut]
                    tags = [t.strip() for t in re.split(r"[,\s]+", raw) if t.strip()]
                    tags_str = ",".join(tags)
                res = ai_tools.convert_note_to_task(note_id=nid, priority=prio, tags=tags_str)
                if streaming_callback:
                    streaming_callback(res)
                return res
            # append note <id> to task <n> [header ...]
            m = re.search(r"\bappend\s+note\s+([a-z0-9-]{4,})\s+to\s+task\s+(\d+)(?:\s+header\s+(.+))?", p)
            if m:
                nid, tid = m.group(1), int(m.group(2))
                header = m.group(3) or ""
                res = ai_tools.append_note_to_task(note_id=nid, task_id=tid, header=header)
                if streaming_callback:
                    streaming_callback(res)
                return res

            # ---- Create task (broad triggers) ----
            # Trigger if mentions 'task' with create/add/new, or a bare 'create' likely for tasks
            creates = ("create task", "add task", "new task")
            broad_create = ("create", "add", "make", "new")
            is_task_intent = any(t in p for t in creates) or (any(b in p for b in broad_create) and "note" not in p)
            if not is_task_intent:
                return None

            # Title extraction (quoted wins)
            name = ""
            m = re.search(r'"([^"]+)"|\'([^\']+)\'', text)
            if m:
                name = m.group(1) or m.group(2) or ""
            else:
                # Heuristic: take words after the first trigger
                lower_text = text.lower()
                # find first occurrence index among triggers
                candidates = []
                for t in list(creates) + list(broad_create):
                    i = lower_text.find(t)
                    if i != -1:
                        candidates.append((i, t))
                if candidates:
                    i, trig = sorted(candidates, key=lambda x: x[0])[0]
                    start = i + len(trig)
                    rest = text[start:].strip().lstrip(':').strip()
                    cutpoints = [len(rest)]
                    for kw in (" priority", " tags", " tag", " with "):
                        k = rest.lower().find(kw)
                        if k != -1:
                            cutpoints.append(k)
                    name = rest[: min(cutpoints)].strip()
            if not name:
                name = "New Task"

            # Priority
            prio = 2
            if "priority" in p:
                if re.search(r"priority\s*(=|:)?\s*1|priority\s*high", p):
                    prio = 1
                elif re.search(r"priority\s*(=|:)?\s*3|priority\s*low", p):
                    prio = 3
                elif re.search(r"priority\s*(=|:)?\s*2|priority\s*medium", p):
                    prio = 2

            # Tags
            tags_str = ""
            tm = re.search(r"tags?\s*(=|:)?\s+(.+)$", text, flags=re.IGNORECASE)
            if tm:
                tags_str = tm.group(2).strip()
                for sep in [".", "\n"]:
                    cut = tags_str.find(sep)
                    if cut != -1:
                        tags_str = tags_str[:cut]
                tags = [t.strip() for t in re.split(r"[,\s]+", tags_str) if t.strip()]
                tags_str = ",".join(tags)

            res = ai_tools.create_task(name=name, priority=prio, tag=tags_str, description="", comment="")
            if streaming_callback:
                streaming_callback(res)
            return res

            # (Unreachable)

        except Exception as e:
            debug_log.error(f"[ASSISTANT] Tool routing failed: {e}", exception=e)
            return None
