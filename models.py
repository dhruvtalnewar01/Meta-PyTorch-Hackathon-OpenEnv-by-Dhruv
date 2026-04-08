"""
CloudDevOps-Env: Pydantic Models
Typed Action, Observation, and State models for the SRE incident debugging environment.
"""

from typing import List, Optional, Dict, Any
from enum import Enum
from openenv.core.env_server import Action, Observation, State


class CommandType(str, Enum):
    """Available command types the agent can execute."""
    QUERY_LOGS = "query_logs"
    CHECK_METRICS = "check_metrics"
    RESTART_SERVICE = "restart_service"
    SCALE_SERVICE = "scale_service"
    KILL_PROCESS = "kill_process"
    ROLLBACK_MIGRATION = "rollback_migration"
    STOP_SERVICE = "stop_service"
    START_SERVICE = "start_service"
    RUN_DIAGNOSTIC = "run_diagnostic"
    APPLY_FIX = "apply_fix"
    VERIFY_HEALTH = "verify_health"
    WAIT = "wait"


class CloudAction(Action):
    """An action the agent takes in the SRE environment."""
    command: CommandType
    target: str = ""         # e.g., service name, process id, migration id
    args: Dict[str, str] = {}  # additional arguments for the command


class CloudObservation(Observation):
    """What the agent observes after taking an action."""
    # done: bool and reward: Optional[float] are inherited from Observation base
    current_alerts: List[str]       # Active alerts in the system
    terminal_output: str            # Output from the last command
    system_health: Dict[str, Any]   # Service health metrics
    available_services: List[str]   # List of services in the infrastructure
    message: str                    # Human-readable feedback
    step_number: int = 0            # Current step in the episode
    task_progress: float = 0.0      # Progress toward task completion (0.0-1.0)


class CloudReward(Action):
    """Reward breakdown for transparency."""
    step_reward: float = 0.0        # Reward for this step
    task_progress: float = 0.0      # Cumulative progress
    penalties: float = 0.0          # Penalties applied


class CloudState(State):
    """Internal state of the environment (episode metadata)."""
    # episode_id: Optional[str] and step_count: int are inherited from State base
    task_name: str = ""
    task_difficulty: str = ""
    total_reward: float = 0.0
    max_steps: int = 20
    services_status: Dict[str, str] = {}
    incident_resolved: bool = False
