"""
Progress display utilities for long-running operations.

Provides progress bars, spinners, and status indicators.
"""

import sys
import time
from typing import Optional, List, Any, Generator
from dataclasses import dataclass
from enum import Enum


class ProgressStyle(Enum):
    """Available progress display styles."""

    BAR = "bar"  # [=====>    ]
    DOTS = "dots"  # Processing...
    SPINNER = "spinner"  # ⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏
    PERCENTAGE = "percentage"  # 45%
    STEPS = "steps"  # Step 3/10


@dataclass
class ProgressConfig:
    """Configuration for progress display."""

    style: ProgressStyle = ProgressStyle.BAR
    width: int = 40
    show_percentage: bool = True
    show_eta: bool = False
    show_speed: bool = False
    color_enabled: bool = True


class ProgressDisplay:
    """
    Progress indicator for long operations.

    Example:
        >>> progress = ProgressDisplay(total=100)
        >>> for i in range(100):
        ...     progress.update(i)
        ...     # do work
        >>> progress.finish()
    """

    # Spinner frames
    SPINNERS = {
        "dots": ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"],
        "line": ["-", "\\", "|", "/"],
        "arrow": ["←", "↖", "↑", "↗", "→", "↘", "↓", "↙"],
        "box": ["◰", "◳", "◲", "◱"],
        "circle": ["◐", "◓", "◑", "◒"],
    }

    def __init__(
        self,
        total: Optional[int] = None,
        description: str = "",
        config: Optional[ProgressConfig] = None,
    ):
        """Initialize progress display."""
        self.total = total
        self.description = description
        self.config = config or ProgressConfig()
        self.current = 0
        self.start_time = time.time()
        self.spinner_frame = 0

    def update(
        self, current: Optional[int] = None, description: Optional[str] = None
    ) -> None:
        """Update progress display."""
        if current is not None:
            self.current = current
        else:
            self.current += 1

        if description is not None:
            self.description = description

        self._render()

    def _render(self) -> None:
        """Render the progress display."""
        if self.config.style == ProgressStyle.BAR:
            self._render_bar()
        elif self.config.style == ProgressStyle.DOTS:
            self._render_dots()
        elif self.config.style == ProgressStyle.SPINNER:
            self._render_spinner()
        elif self.config.style == ProgressStyle.PERCENTAGE:
            self._render_percentage()
        elif self.config.style == ProgressStyle.STEPS:
            self._render_steps()

    def _render_bar(self) -> None:
        """Render progress bar."""
        if not self.total:
            return

        percentage = self.current / self.total
        filled = int(self.config.width * percentage)
        bar = "=" * filled + ">" + " " * (self.config.width - filled - 1)

        line = f"\r{self.description} [{bar}]"

        if self.config.show_percentage:
            line += f" {int(percentage * 100)}%"

        if self.config.show_eta:
            eta = self._calculate_eta()
            if eta:
                line += f" ETA: {eta}"

        sys.stdout.write(line)
        sys.stdout.flush()

    def _render_dots(self) -> None:
        """Render dots progress."""
        dots = "." * (self.current % 4)
        line = f"\r{self.description}{dots}    "
        sys.stdout.write(line)
        sys.stdout.flush()

    def _render_spinner(self) -> None:
        """Render spinner."""
        frames = self.SPINNERS["dots"]
        frame = frames[self.spinner_frame % len(frames)]
        self.spinner_frame += 1

        line = f"\r{frame} {self.description}"

        if self.total and self.config.show_percentage:
            percentage = int((self.current / self.total) * 100)
            line += f" {percentage}%"

        sys.stdout.write(line)
        sys.stdout.flush()

    def _render_percentage(self) -> None:
        """Render percentage only."""
        if not self.total:
            return

        percentage = int((self.current / self.total) * 100)
        line = f"\r{self.description} {percentage}%"
        sys.stdout.write(line)
        sys.stdout.flush()

    def _render_steps(self) -> None:
        """Render step counter."""
        if self.total:
            line = f"\r{self.description} Step {self.current}/{self.total}"
        else:
            line = f"\r{self.description} Step {self.current}"

        sys.stdout.write(line)
        sys.stdout.flush()

    def _calculate_eta(self) -> Optional[str]:
        """Calculate estimated time remaining."""
        if not self.total or self.current == 0:
            return None

        elapsed = time.time() - self.start_time
        rate = self.current / elapsed
        remaining = (self.total - self.current) / rate

        if remaining < 60:
            return f"{int(remaining)}s"
        elif remaining < 3600:
            return f"{int(remaining / 60)}m"
        else:
            return f"{int(remaining / 3600)}h"

    def finish(self, message: Optional[str] = None) -> None:
        """Complete the progress display."""
        if message:
            print(f"\r{message}")
        else:
            print()  # New line


def print_progress(
    items: List[Any],
    description: str = "Processing",
    style: ProgressStyle = ProgressStyle.BAR,
) -> Generator[Any, None, None]:
    """
    Process items with progress display.

    Args:
        items: Items to process
        description: Progress description
        style: Progress display style

    Example:
        >>> items = range(100)
        >>> for item in print_progress(items, "Loading"):
        ...     # Process item
        ...     time.sleep(0.01)
    """
    config = ProgressConfig(style=style)
    progress = ProgressDisplay(len(items), description, config)

    for i, item in enumerate(items):
        progress.update(i)
        yield item

    progress.finish()


class StatusDisplay:
    """
    Status indicator for multi-step operations.

    Example:
        >>> status = StatusDisplay()
        >>> status.start("Connecting to database")
        >>> # do work
        >>> status.success()
        >>> status.start("Loading data")
        >>> # do work
        >>> status.success()
    """

    SYMBOLS = {
        "pending": "⋯",
        "running": "→",
        "success": "✓",
        "error": "✗",
        "warning": "⚠",
        "skip": "↓",
    }

    def __init__(self):
        """Initialize status display."""
        self.current_task = None
        self.completed_tasks = []

    def start(self, task: str) -> None:
        """Start a new task."""
        if self.current_task:
            self.error("Incomplete")

        self.current_task = task
        print(f"{self.SYMBOLS['running']} {task}...", end="", flush=True)

    def success(self, message: str = "Done") -> None:
        """Mark current task as successful."""
        if self.current_task:
            print(f"\r{self.SYMBOLS['success']} {self.current_task}: {message}")
            self.completed_tasks.append((self.current_task, "success"))
            self.current_task = None

    def error(self, message: str = "Failed") -> None:
        """Mark current task as failed."""
        if self.current_task:
            print(f"\r{self.SYMBOLS['error']} {self.current_task}: {message}")
            self.completed_tasks.append((self.current_task, "error"))
            self.current_task = None

    def warning(self, message: str = "Warning") -> None:
        """Mark current task with warning."""
        if self.current_task:
            print(f"\r{self.SYMBOLS['warning']} {self.current_task}: {message}")
            self.completed_tasks.append((self.current_task, "warning"))
            self.current_task = None

    def skip(self, message: str = "Skipped") -> None:
        """Mark current task as skipped."""
        if self.current_task:
            print(f"\r{self.SYMBOLS['skip']} {self.current_task}: {message}")
            self.completed_tasks.append((self.current_task, "skip"))
            self.current_task = None

    def summary(self) -> None:
        """Print summary of all tasks."""
        print("\nSummary:")
        print("-" * 40)

        counts = {"success": 0, "error": 0, "warning": 0, "skip": 0}

        for task, status in self.completed_tasks:
            symbol = self.SYMBOLS[status]
            print(f"  {symbol} {task}")
            counts[status] += 1

        print("-" * 40)
        print(f"  Total: {len(self.completed_tasks)} tasks")
        print(f"  ✓ Success: {counts['success']}")
        if counts["error"]:
            print(f"  ✗ Errors: {counts['error']}")
        if counts["warning"]:
            print(f"  ⚠ Warnings: {counts['warning']}")
        if counts["skip"]:
            print(f"  ↓ Skipped: {counts['skip']}")
