"""
Industrial Mind & Code - Experiment Tracker
Logs experiment runs, agent calls, and results.
"""

import json
import logging
from datetime import datetime
from pathlib import Path


class ExperimentTracker:
    """Track experiment runs and agent behavior."""

    def __init__(self, experiment_name, results_dir='./results'):
        self.experiment_name = experiment_name
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        (self.results_dir / 'logs').mkdir(exist_ok=True)
        (self.results_dir / 'figures').mkdir(exist_ok=True)
self.run_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.log_file = self.results_dir / 'logs' / f'run_{self.run_id}.json'
        self.events = []

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(
                    self.results_dir / 'logs' / f'run_{self.run_id}.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(experiment_name)

    def log_event(self, event_type, data):
        """Log an event (agent call, result, error)."""
        event = {
            'timestamp': datetime.now().isoformat(),
            'type': event_type,
            'data': data
        }
        self.events.append(event)
        self.logger.info(f'[{event_type}] {json.dumps(data)[:200]}')

    def save(self):
        """Save all events to the log file."""
        with open(self.log_file, 'w') as f:
            json.dump({
                'experiment': self.experiment_name,
                'run_id': self.run_id,
                'events': self.events
            }, f, indent=2)
        self.logger.info(f'Saved {len(self.events)} events to {self.log_file}')
