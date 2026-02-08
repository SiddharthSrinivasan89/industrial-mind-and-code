"""
Industrial Mind & Code - Experiment ##: [Title]
The factory mind, brought to life through code.
Run: python src/main.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

# Load .env from project root
project_root = Path(__file__).resolve().parents[3]
load_dotenv(project_root / '.env')

# Add shared utilities to path
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from shared.utils.azure_client import get_azure_client
from shared.utils.tracker import ExperimentTracker

console = Console()


def main():
    console.print(Panel(
        '[bold]Industrial Mind & Code[/bold]\n'
        'Experiment ##: [Title]\n'
        '[dim]The factory mind, brought to life through code.[/dim]',
        style='blue'
    ))

    # Initialize
    client = get_azure_client()
    tracker = ExperimentTracker('imc-experiment-##')
    tracker.log_event('start', {'status': 'initialized'})

    # ================================================
    # YOUR EXPERIMENT LOGIC GOES HERE
    # ================================================
    #
    # 1. Load scenario data from data/raw/
    # 2. Initialize agents (from agents/ folder)
    # 3. Run agents on scenarios
    # 4. Collect and log results
    # 5. Save outputs to results/
    # ================================================

    tracker.log_event('complete', {'status': 'done'})
    tracker.save()
    console.print('\n[green]\u2713 Experiment complete. Results saved.[/green]')


if __name__ == '__main__':
    main()
