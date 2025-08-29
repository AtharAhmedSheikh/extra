from rich.console import Console

console = Console()

# Global flag for enabling/disabling logs
_logs_enabled = False

def enable_verbose_logging():
    """Enable verbose logging output globally."""
    global _logs_enabled
    _logs_enabled = True

class Logger:
    """Rich console print wrapper for structured logging."""
    @classmethod
    def _log(cls, message: str, style: str):
        """Internal logging function."""
        if _logs_enabled:
            console.print(message, style=style)

    @classmethod
    def info(cls, message: str):
        cls._log(f"[INFO] {message}", style="cyan")

    @classmethod
    def success(cls, message: str):
        cls._log(f"[SUCCESS] {message}", style="green")

    @classmethod
    def warning(cls, message: str):
        cls._log(f"[WARNING] {message}", style="yellow")

    @classmethod
    def error(cls, message: str):
        cls._log(f"[ERROR] {message}", style="bold red")

    @classmethod
    def debug(cls, message: str):
        cls._log(f"[DEBUG] {message}", style="dim")

