from rich.console import Console

def show_help():
    """Display simple Rich-styled help information"""
    
    console = Console()
    
    # Simple title
    console.print("\n[bold blue]Reportr[/bold blue] - AI-powered repository analysis tool\n")
    
    # Commands
    console.print("[bold]Available Commands:[/bold]")
    console.print("  [green]progress-report[/green]    Generate a progress report")
    console.print("  [green]generate-readme[/green]    Generate a README file")
    console.print("  [green]summarize-details[/green]  Detailed directory analysis")
    console.print("  [green]summarize-overview[/green] Repository overview")
    
    # Examples
    console.print("\n[bold]Examples:[/bold]")
    console.print("  python reportr.py [sky_blue1]progress-report[/sky_blue1]")
    console.print("  python reportr.py [sky_blue1]progress-report[/sky_blue1] --username [white]dev1[/white] --days [white]7[/white]")
    console.print("  python reportr.py [sky_blue1]summarize-details[/sky_blue1] --path [white]/path/to/repo[/white]")
    
    # Options
    console.print("\n[bold]Common Options:[/bold]")
    console.print("  [plum2]--path[/plum2]      Path to repository (default: current directory)")
    console.print("  [plum2]--username[/plum2]  Filter by contributor username")
    console.print("  [plum2]--days[/plum2]      Days to look back (default: [white]30[/white])")
    console.print("  [plum2]--detailed[/plum2]  Include detailed summaries")
    console.print()
