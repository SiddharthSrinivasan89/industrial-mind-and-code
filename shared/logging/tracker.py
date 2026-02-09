"""
Experiment Tracking Utilities for Industrial Mind & Code
Logs events, parameters, and results with timestamps.
"""

import json
from pathlib import Path
from datetime import datetime
import uuid


class ExperimentTracker:
    """
    Tracks experiment runs with event logging and result storage.
    """
    
    def __init__(self, experiment_id):
        """
        Initialize tracker for a specific experiment.
        
        Args:
            experiment_id: Unique identifier for the experiment (e.g., 'imc-01-agentic-bullwhip-effect')
        """
        self.experiment_id = experiment_id
        self.run_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.start_time = datetime.now().isoformat()
        self.events = []
        self.parameters = {}
        self.results = {}
        
        # Set up results directory
        self.results_dir = Path(f'results/logs')
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.results_dir / f'run_{self.run_id}.json'
    
    def log_event(self, event_type, data=None):
        """
        Log an event with timestamp.
        
        Args:
            event_type: Type of event (e.g., 'start', 'agent_decision', 'complete')
            data: Optional dictionary of event data
        """
        event = {
            'timestamp': datetime.now().isoformat(),
            'type': event_type,
            'data': data or {}
        }
        self.events.append(event)
    
    def set_parameters(self, params):
        """
        Store experiment parameters.
        
        Args:
            params: Dictionary of parameter names and values
        """
        self.parameters.update(params)
    
    def store_results(self, results):
        """
        Store experiment results.
        
        Args:
            results: Dictionary of result names and values
        """
        self.results.update(results)
    
    def save(self):
        """
        Save all tracking data to JSON file.
        """
        output = {
            'experiment_id': self.experiment_id,
            'run_id': self.run_id,
            'start_time': self.start_time,
            'end_time': datetime.now().isoformat(),
            'parameters': self.parameters,
            'events': self.events,
            'results': self.results
        }
        
        with open(self.log_file, 'w') as f:
            json.dump(output, f, indent=2)
        
        return self.log_file
    
    def get_summary(self):
        """
        Return a summary of the experiment run.
        """
        return {
            'experiment_id': self.experiment_id,
            'run_id': self.run_id,
            'num_events': len(self.events),
            'parameters': self.parameters,
            'results': self.results
        }
