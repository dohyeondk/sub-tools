from contextlib import contextmanager

from rich import print
from rich.console import Console
from rich.panel import Panel
from rich.theme import Theme

theme = Theme(
    {
        "info": "bold cyan",
        "success": "bold green",
        "warning": "bold yellow",
        "error": "bold red",
        "highlight": "bold magenta",
    }
)

console = Console(theme=theme)


def header(title: str):
    print(Panel(f"[bold cyan]{title}"))


def info(message: str) -> None:
    console.print(f"[info] :information_source: {message}[/info]")


def success(message: str) -> None:
    console.print(f"[success] :white_check_mark:  {message}[/success] ")


def warning(message: str) -> None:
    console.print(f"[warning] :warning:  {message}[/warning]")


def error(message: str) -> None:
    console.print(f"[error] :cross_mark:  {message}[/error]")


def log(text):
    console.log(text)


@contextmanager
def status(title):
    with console.status(title):
        yield
