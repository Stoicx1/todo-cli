"""
Debug Logger for AI Flow Debugging
Writes timestamped debug events to debug_ai_flow.log
"""

import os
from datetime import datetime
from pathlib import Path


class DebugLogger:
    """Simple debug logger for AI flow tracing with rolling limit."""

    MAX_LINES = 2000
    TRIM_TO = 1500  # when exceeding MAX_LINES, keep last TRIM_TO lines

    def __init__(self, log_file="debug_ai_flow.log"):
        self.log_file = Path(log_file)
        self._lock = None
        try:
            import threading
            self._lock = threading.Lock()
        except Exception:
            self._lock = None
        # Do not clear on start; maintain rolling history
        self._ensure_header()

    def clear(self):
        """Clear the log file"""
        try:
            with open(self.log_file, 'w', encoding='utf-8') as f:
                f.write("")
        except:
            pass

    def write(self, message: str, level="INFO"):
        """Write a timestamped message to log with rolling limit."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        log_line = f"{timestamp} [{level}] {message}\n"

        try:
            if self._lock:
                self._lock.acquire()
            # Append line
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_line)
            # Enforce rolling limit
            self._enforce_limit()
        except Exception as e:
            print(f"Failed to write to log: {e}")
        finally:
            if self._lock:
                try:
                    self._lock.release()
                except Exception:
                    pass

    def _ensure_header(self):
        """Ensure file exists and has a session header."""
        try:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            if not self.log_file.exists() or self.log_file.stat().st_size == 0:
                self.write("=" * 80)
                self.write(f"Debug log started at {datetime.now()}")
                self.write("=" * 80)
        except Exception:
            pass

    def _enforce_limit(self):
        """Trim the file to last TRIM_TO lines if it exceeds MAX_LINES."""
        try:
            # Fast path: count roughly by size; fall back to line count
            with open(self.log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            if len(lines) > self.MAX_LINES:
                tail = lines[-self.TRIM_TO:]
                tmp = self.log_file.with_suffix(self.log_file.suffix + '.tmp')
                with open(tmp, 'w', encoding='utf-8') as tf:
                    tf.writelines(tail)
                # Atomic replace
                try:
                    import os
                    os.replace(tmp, self.log_file)
                except Exception:
                    # Fallback non-atomic
                    with open(self.log_file, 'w', encoding='utf-8') as f:
                        f.writelines(tail)
        except Exception:
            # Best-effort; ignore trimming failures
            pass

    def debug(self, message: str):
        """Write debug message"""
        self.write(message, "DEBUG")

    def info(self, message: str):
        """Write info message"""
        self.write(message, "INFO")

    def error(self, message: str, exception=None):
        """Write error message with optional exception"""
        self.write(message, "ERROR")
        if exception:
            import traceback
            tb = traceback.format_exc()
            for line in tb.split('\n'):
                if line.strip():
                    self.write(f"  {line}", "ERROR")


# Global logger instance
debug_log = DebugLogger()
