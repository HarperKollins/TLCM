# -*- coding: utf-8 -*-
import sys
import io
# Force UTF-8 output on Windows terminals
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

"""
TLCM Command Line Interface
The main entry point to interact with the system.
Built with Rich for beautiful terminal output.
"""

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text
from rich import print as rprint
from typing import Optional

from core.database import init_db
from core.workspace import WorkspaceManager
from core.epoch import EpochManager
from core.memory_store import MemoryStore
from core.temporal_jump import TemporalJumpEngine
from core.chat import TLCMChat

app = typer.Typer(help="TLCM — Temporal Layered Context Memory Engine")
console = Console()

workspaces = WorkspaceManager()
epochs = EpochManager()
memory = MemoryStore()
jumper = TemporalJumpEngine()


# ─── WORKSPACE COMMANDS ───────────────────────────────────────────────────────

workspace_app = typer.Typer(help="Manage cognitive workspaces")
app.add_typer(workspace_app, name="workspace")


@workspace_app.command("create")
def workspace_create(
    name: str = typer.Argument(..., help="Workspace name (e.g. 'HK AI')"),
    desc: str = typer.Option("", "--desc", "-d", help="Description"),
):
    """Create a new isolated cognitive workspace."""
    result = workspaces.create(name, desc)
    console.print(Panel(
        f"[bold green]OK Workspace created[/]\n"
        f"Name: [cyan]{name}[/]\n"
        f"ID: [dim]{result['id'][:12]}...[/]",
        title="[bold]New Workspace",
    ))


@workspace_app.command("list")
def workspace_list():
    """List all workspaces."""
    all_ws = workspaces.list_all()
    if not all_ws:
        console.print("[dim]No workspaces yet. Create one with: tlcm workspace create 'Name'[/]")
        return

    table = Table(title="[bold]Cognitive Workspaces", show_header=True)
    table.add_column("Name", style="cyan")
    table.add_column("Memories", justify="right")
    table.add_column("Description")
    table.add_column("Created", style="dim")
    for ws in all_ws:
        table.add_row(
            ws["name"],
            str(ws.get("memory_count", 0)),
            ws.get("description", ""),
            ws["created_at"][:10],
        )
    console.print(table)


@workspace_app.command("link")
def workspace_link(
    source: str = typer.Argument(...),
    target: str = typer.Argument(...),
    reason: str = typer.Option(..., "--reason", "-r"),
):
    """Explicitly authorize a cross-workspace link."""
    workspaces.authorize_link(source, target, reason)
    console.print(f"[green]OK Authorized: '{source}' <-> '{target}'[/]")


# ─── EPOCH COMMANDS ───────────────────────────────────────────────────────────

epoch_app = typer.Typer(help="Manage temporal epochs")
app.add_typer(epoch_app, name="epoch")


@epoch_app.command("create")
def epoch_create(
    workspace: str = typer.Argument(...),
    name: str = typer.Argument(...),
    desc: str = typer.Option("", "--desc", "-d"),
    start: str = typer.Option(None, "--start"),
    end: str = typer.Option(None, "--end"),
):
    """Create a new temporal epoch in a workspace."""
    ws = workspaces.get(workspace)
    if not ws:
        console.print(f"[red]Workspace '{workspace}' not found.[/]")
        raise typer.Exit(1)
    result = epochs.create(ws["id"], name, desc, start, end)
    console.print(f"[green]OK Epoch '{name}' created in '{workspace}'[/]")


@epoch_app.command("list")
def epoch_list(workspace: str = typer.Argument(...)):
    """List all epochs in a workspace."""
    ws = workspaces.get(workspace)
    if not ws:
        console.print(f"[red]Workspace '{workspace}' not found.[/]")
        raise typer.Exit(1)

    all_epochs = epochs.list_epochs(ws["id"])
    table = Table(title=f"Epochs in [cyan]{workspace}[/]")
    table.add_column("Name", style="cyan")
    table.add_column("Status")
    table.add_column("Memories", justify="right")
    table.add_column("Start")
    table.add_column("End")
    for e in all_epochs:
        status = "[green]Active[/]" if e["is_active"] else "[dim]Closed[/]"
        table.add_row(
            e["name"], status,
            str(e.get("memory_count", 0)),
            (e.get("start_date") or "")[:10],
            (e.get("end_date") or "present")[:10],
        )
    console.print(table)


# ─── MEMORY COMMANDS ──────────────────────────────────────────────────────────

@app.command("remember")
def remember(
    workspace: str = typer.Option(..., "--workspace", "-w"),
    content: str = typer.Argument(...),
    epoch: Optional[str] = typer.Option(None, "--epoch", "-e"),
):
    """Store a new memory in a workspace."""
    result = memory.remember(content, workspace, epoch)
    console.print(f"[green]OK Remembered in '{workspace}' / '{result['epoch']}'[/]")
    console.print(f"  [dim]ID: {result['id'][:12]}...[/]")


@app.command("recall")
def recall(
    workspace: str = typer.Option(..., "--workspace", "-w"),
    query: str = typer.Argument(...),
    epoch: Optional[str] = typer.Option(None, "--epoch", "-e"),
    limit: int = typer.Option(5, "--limit", "-n"),
):
    """Recall memories from a workspace by semantic search."""
    results = memory.recall(query, workspace, epoch, limit)
    if not results:
        console.print(f"[dim]No memories found for '{query}' in workspace '{workspace}'[/]")
        return

    console.print(Panel(
        f"[bold]Recalling:[/] '{query}'\n"
        f"[dim]Workspace: {workspace}{f' / {epoch}' if epoch else ''}[/]",
    ))
    for i, m in enumerate(results, 1):
        rprint(f"[cyan]{i}.[/] {m['content']}")
        rprint(f"   [dim]v{m['version']} | {m['created_at'][:10]} | {m.get('source', '')}[/]")
        rprint(f"   [dim]id: {m['id'][:12]}...[/]")


@app.command("history")
def history(memory_id: str = typer.Argument(...)):
    """Show the full version history of a memory (the temporal arc of a belief)."""
    chain = memory.get_version_history(memory_id)
    if not chain:
        console.print("[red]Memory not found.[/]")
        return

    console.print(Panel("[bold]Memory Version History[/] — Full Belief Arc", style="cyan"))
    for m in chain:
        status = "[green]CURRENT[/]" if m["is_current"] else "[dim]ARCHIVED[/]"
        console.print(f"\n  [bold]v{m['version']}[/] {status}")
        console.print(f"  Content: {m['content']}")
        console.print(f"  [dim]Date: {m['created_at'][:16]}[/]")
        if m.get("update_reason"):
            console.print(f"  [yellow]Updated because:[/] {m['update_reason']}")


# ─── TEMPORAL JUMP ────────────────────────────────────────────────────────────

@app.command("jump")
def jump(
    workspace: str = typer.Option(..., "--workspace", "-w"),
    from_epoch: str = typer.Option(..., "--from", "-f"),
    to_epoch: Optional[str] = typer.Option(None, "--to", "-t"),
    query: Optional[str] = typer.Option(None, "--query", "-q"),
):
    """
    Perform a temporal jump between epochs.
    Reconstructs the world-state at each epoch and maps the arc.
    """
    console.print(Panel(
        f"[bold]Temporal Jump[/]\n"
        f"Workspace: [cyan]{workspace}[/]\n"
        f"From: [yellow]{from_epoch}[/] → To: [green]{to_epoch or 'current'}[/]",
    ))
    with console.status("[bold yellow]Jumping through time...[/]"):
        result = jumper.jump(workspace, from_epoch, to_epoch, query)
    console.print(Panel(result, title="[bold cyan]Temporal Analysis[/]", border_style="cyan"))


# ─── INTERACTIVE CHAT ─────────────────────────────────────────────────────────

@app.command("chat")
def chat(
    workspace: str = typer.Option(..., "--workspace", "-w"),
    epoch: Optional[str] = typer.Option(None, "--epoch", "-e"),
):
    """
    Start an interactive chat session within a workspace.
    Type /remember <fact> to store something.
    Type /jump <from_epoch> to perform a temporal jump.
    Type /history <memory_id> to see version history.
    Type /exit to quit.
    """
    console.print(Panel(
        f"[bold cyan]TLCM Chat[/]\n"
        f"Workspace: [green]{workspace}[/]\n"
        f"Epoch: [yellow]{epoch or 'auto-active'}[/]\n\n"
        f"[dim]Commands: /remember <fact> | /jump <from_epoch> | /history <id> | /exit[/]",
        title="[bold]Temporal Layered Context Memory",
    ))

    session = TLCMChat(workspace_name=workspace, epoch_name=epoch)

    while True:
        try:
            user_input = Prompt.ask("\n[bold cyan]You[/]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Session ended.[/]")
            break

        if user_input.strip().lower() == "/exit":
            console.print("[dim]Goodbye.[/]")
            break

        elif user_input.startswith("/remember "):
            fact = user_input[len("/remember "):].strip()
            result = session.remember_this(fact)
            console.print(f"[green]{result}[/]")

        elif user_input.startswith("/jump "):
            from_e = user_input[len("/jump "):].strip()
            with console.status("[yellow]Jumping...[/]"):
                result = session.temporal_jump(from_e)
            console.print(Panel(result, title="Temporal Jump", border_style="yellow"))

        elif user_input.startswith("/history "):
            mid = user_input[len("/history "):].strip()
            chain = memory.get_version_history(mid)
            for m in chain:
                console.print(f"v{m['version']}: {m['content']} [dim]({m['created_at'][:10]})[/]")

        else:
            with console.status("[dim]Thinking...[/]"):
                reply = session.chat(user_input)
            console.print(f"\n[bold green]TLCM[/]: {reply}")


# ─── INIT ─────────────────────────────────────────────────────────────────────

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """TLCM — Temporal Layered Context Memory Engine"""
    init_db()
    if ctx.invoked_subcommand is None:
        console.print(Panel(
            "[bold cyan]TLCM — Temporal Layered Context Memory[/]\n\n"
            "Use [green]tlcm --help[/] to see all commands.\n\n"
            "[dim]Based on the thesis by Collins Somtochukwu (Harper Kollins), April 2026[/]",
            border_style="cyan",
        ))


if __name__ == "__main__":
    app()
