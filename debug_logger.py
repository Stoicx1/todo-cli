"""
Comprehensive debug logger for Todo CLI.

Features:
- Thread-safe writes with rolling limit
- Optional JSON lines output
- Context (module:function:line, thread) tagging
- Spans / timing context managers
- Configurable via environment variables

Env vars:
  TODO_DEBUG_FILE (default: debug_ai_flow.log)
  TODO_DEBUG_JSON (1/0, default 0)
  TODO_DEBUG_ECHO (1/0, default 0)
  TODO_DEBUG_LEVEL (DEBUG/INFO/WARNING/ERROR, default INFO)
"""

from __future__ import annotations

import os
import json
import time
import inspect
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager


_LEVELS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40}


class DebugLogger:
    """Comprehensive debug logger with spans and JSON output."""

    MAX_LINES = 5000
    TRIM_TO = 4000  # when exceeding MAX_LINES, keep last TRIM_TO lines

    def __init__(
        self,
        log_file: str | None = None,
        *,
        json_mode: bool | None = None,
        echo: bool | None = None,
        level: str | None = None,
    ):
        self.log_file = Path(log_file or os.environ.get("TODO_DEBUG_FILE", "debug_ai_flow.log"))
        self.json_mode = bool(int(os.environ.get("TODO_DEBUG_JSON", "0"))) if json_mode is None else json_mode
        self.echo = bool(int(os.environ.get("TODO_DEBUG_ECHO", "0"))) if echo is None else echo
        self.level_name = (level or os.environ.get("TODO_DEBUG_LEVEL", "INFO")).upper()
        self.level = _LEVELS.get(self.level_name, 20)

        try:
            import threading

            self._lock = threading.Lock()
        except Exception:
            self._lock = None

        self._ensure_header()

    def set_level(self, level: str) -> None:
        self.level_name = level.upper()
        self.level = _LEVELS.get(self.level_name, 20)

    def clear(self) -> None:
        try:
            with open(self.log_file, "w", encoding="utf-8") as f:
                f.write("")
        except Exception:
            pass

    def _ctx(self):
        """Return (module,function,line,thread) context for the caller."""
        module_name = func = "?"
        line = 0
        try:
            frame = inspect.stack()[3]  # skip write->level method->caller
            mod = inspect.getmodule(frame.frame)
            module_name = getattr(mod, "__name__", "?") if mod else "?"
            func = frame.function
            line = frame.lineno
            import threading as _t

            thr = _t.current_thread().name
        except Exception:
            thr = "?"
        return module_name, func, line, thr

    def _should_log(self, level: str) -> bool:
        return _LEVELS.get(level, 99) >= self.level

    def write(self, message: str, level: str = "INFO", **extra) -> None:
        if not self._should_log(level):
            return

        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        module_name, func, line, thr = self._ctx()

        try:
            if self._lock:
                self._lock.acquire()

            if self.json_mode:
                payload = {
                    "ts": ts,
                    "level": level,
                    "msg": message,
                    "module": module_name,
                    "func": func,
                    "line": line,
                    "thread": thr,
                }
                if extra:
                    payload.update(extra)
                line_out = json.dumps(payload, ensure_ascii=False) + "\n"
            else:
                context = f"{module_name}:{func}:{line} [thr={thr}]"
                meta = (" " + json.dumps(extra, ensure_ascii=False) if extra else "")
                line_out = f"{ts} [{level}] {context}  {message}{meta}\n"

            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(line_out)

            if self.echo:
                try:
                    print(line_out, end="")
                except Exception:
                    pass

            self._enforce_limit()
        except Exception as e:
            try:
                print(f"Failed to write to log: {e}")
            except Exception:
                pass
        finally:
            if self._lock:
                try:
                    self._lock.release()
                except Exception:
                    pass

    def _ensure_header(self) -> None:
        try:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            if not self.log_file.exists() or self.log_file.stat().st_size == 0:
                self.write("=" * 80)
                self.write(f"Debug log started at {datetime.now().isoformat(timespec='seconds')}")
                self.write("=" * 80)
        except Exception:
            pass

    def _enforce_limit(self) -> None:
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
            if len(lines) > self.MAX_LINES:
                tail = lines[-self.TRIM_TO :]
                tmp = self.log_file.with_suffix(self.log_file.suffix + ".tmp")
                with open(tmp, "w", encoding="utf-8") as tf:
                    tf.writelines(tail)
                try:
                    os.replace(tmp, self.log_file)
                except Exception:
                    with open(self.log_file, "w", encoding="utf-8") as f:
                        f.writelines(tail)
        except Exception:
            pass

    # Convenience level methods
    def debug(self, message: str, **extra) -> None:
        self.write(message, "DEBUG", **extra)

    def info(self, message: str, **extra) -> None:
        self.write(message, "INFO", **extra)

    def warning(self, message: str, **extra) -> None:
        self.write(message, "WARNING", **extra)

    def error(self, message: str, exception=None, **extra) -> None:
        self.write(message, "ERROR", **extra)
        if exception:
            import traceback

            tb = traceback.format_exc()
            for line in tb.split("\n"):
                if line.strip():
                    self.write(f"  {line}", "ERROR")

    # Spans / timing helpers
    @contextmanager
    def span(self, name: str, **extra):
        """Timing span helper for structured debug logs."""
        start = time.perf_counter()
        self.debug(f">> {name} - start", **extra)
        try:
            yield
        except Exception as e:
            self.error(f"!! {name} - error: {e}", exception=e, **extra)
            raise
        finally:
            dur_ms = (time.perf_counter() - start) * 1000.0
            self.debug(f"<< {name} - done in {dur_ms:.1f}ms", duration_ms=round(dur_ms, 1), **extra)


# Global logger instance (backward compatible import)
debug_log = DebugLogger()

