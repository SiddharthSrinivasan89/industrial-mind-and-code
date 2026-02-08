"""
Industrial Mind & Code - Experiment 01: Agentic Bullwhip Effect
The factory mind, brought to life through code.
Run: python src/main.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

# Add project root to path (go up 2 levels: src -> experiment -> experiments -> project_root)
# From: /home/sid/industrial-mind-and-code/experiments/imc-01-agentic-bullwhip-effect/src/main.py
# To:   /home/sid/industrial-mind-and-code
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

# Load .env from project root
load_dotenv(project_root / '.env')

from shared.utils.azure_client import get_azure_client
from shared.utils.tracker import ExperimentTracker

console = Console()


def main():
    console.print(Panel(
        '[bold]Industrial Mind & Code[/bold]\n'
        'Experiment 01: Agentic Bullwhip Effect\n'
        '[dim]The factory mind, brought to life through code.[/dim]',
        style='blue'
    ))

    # Initialize
    client = get_azure_client()
    tracker = ExperimentTracker('imc-01-agentic-bullwhip-effect')
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
    console.print('\n[green]✓ Experiment complete. Results saved.[/green]')


if __name__ == '__main__':
    main()
