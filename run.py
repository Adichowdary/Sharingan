#!/usr/bin/env python3
"""
PhishGuard — Run Script
Start the server with: python run.py
"""
import uvicorn
from rich.console import Console
from rich.panel import Panel

from app.config import settings

console = Console()


def main():
    console.print(Panel.fit(
        f"[bold magenta]🛡️  {settings.PROJECT_NAME} v{settings.VERSION}[/bold magenta]\n"
        f"[dim]{settings.DESCRIPTION}[/dim]\n\n"
        f"[green]Dashboard:[/green]  {settings.BASE_URL}\n"
        f"[green]API Docs:[/green]   {settings.BASE_URL}/docs\n"
        f"[green]Host:[/green]       {settings.HOST}:{settings.PORT}",
        title="PhishGuard Server",
        border_style="bright_magenta",
    ))

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
    )


if __name__ == "__main__":
    main()
