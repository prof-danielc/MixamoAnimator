import inquirer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from typing import List, Dict, Optional


class UI:
    """
    Handles the interactive terminal user interface using inquirer and rich.
    """

    def __init__(self):
        self.console = Console()

    def get_credentials(self, default_email: str = "") -> Dict[str, str]:
        """
        Prompts the user for Mixamo email and password.
        """
        questions = [
            inquirer.Text('email', message="Enter your Mixamo email", default=default_email),
            inquirer.Password('password', message="Enter your Mixamo password")
        ]
        answers = inquirer.prompt(questions)
        if not answers:
            return {"email": "", "password": ""}
        return answers

    def select_animations(self, animation_catalog: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Displays a list of animations and allows multi-selection.
        Supports "Select All".
        Returns a list of dicts: [{"id": "...", "name": "..."}]
        """
        if not animation_catalog:
            self.console.print("[yellow]No animations found in catalog.[/yellow]")
            return []

        # Create choices for inquirer.
        # Checkbox expects a list of (label, value) tuples.
        # We'll use (name, index) tuples so we can easily map back to the full dict.
        choices = [("Select All", "all")] + [(anim['name'], i) for i, anim in enumerate(animation_catalog)]
        
        questions = [
            inquirer.Checkbox(
                'selected',
                message="Select animations to download (Space to select, Enter to confirm)",
                choices=choices,
            )
        ]
        
        answers = inquirer.prompt(questions)
        if not answers:
            return []
            
        selected_indices = answers.get('selected', [])
        
        if "all" in selected_indices:
            return animation_catalog
        
        return [animation_catalog[i] for i in selected_indices if i != "all"]

    def create_progress_bar(self) -> Progress:
        """
        Creates and returns a rich Progress object to track downloads.
        """
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=self.console,
            transient=True
        )

    def display_api_status(self, active: bool):
        """Displays whether the API client is active/authenticated."""
        status = "[bold green]Active[/bold green]" if active else "[bold yellow]Inactive (Fallback to Playwright)[/bold yellow]"
        self.console.print(f"Mixamo API Status: {status}")

    def print_message(self, message: str, style: str = "white"):
        """Prints a message with the specified rich style."""
        self.console.print(message, style=style)

    def print_error(self, message: str):
        """Prints an error message in red."""
        self.console.print(f"[bold red]Error:[/bold red] {message}")

    def print_success(self, message: str):
        """Prints a success message in green."""
        self.console.print(f"[bold green]Success:[/bold green] {message}")

    def print_header(self, message: str):
        """Prints a header message."""
        self.console.print(f"\n[bold cyan]=== {message} ===[/bold cyan]\n")
