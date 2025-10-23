"""
Debug Logger for AI Flow Debugging
Writes timestamped debug events to debug_ai_flow.log
"""

import os
from datetime import datetime
from pathlib import Path


class DebugLogger:
    """Simple debug logger for AI flow tracing"""

    def __init__(self, log_file="debug_ai_flow.log"):
        self.log_file = Path(log_file)
        # Clear log file on app start
        self.clear()
        self.write("=" * 80)
        self.write(f"Debug log started at {datetime.now()}")
        self.write("=" * 80)

    def clear(self):
        """Clear the log file"""
        try:
            with open(self.log_file, 'w', encoding='utf-8') as f:
                f.write("")
        except:
            pass

    def write(self, message: str, level="INFO"):
        """Write a timestamped message to log"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        log_line = f"{timestamp} [{level}] {message}\n"

        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_line)
        except Exception as e:
            print(f"Failed to write to log: {e}")

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
