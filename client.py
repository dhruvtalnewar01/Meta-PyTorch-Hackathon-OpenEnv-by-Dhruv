"""
CloudDevOps-Env: Client
Translates between typed models and the WebSocket wire format.
"""

from openenv.core.env_client import EnvClient
from openenv.core.client_types import StepResult
from .models import CloudAction, CloudObservation, CloudState


class CloudDevOpsEnv(EnvClient[CloudAction, CloudObservation, CloudState]):
    """Client for connecting to the CloudDevOps environment server."""

    def _step_payload(self, action: CloudAction) -> dict:
        """Convert a CloudAction to a wire-format dict."""
        return {
            "command": action.command.value,
            "target": action.target,
            "args": action.args,
        }

    def _parse_result(self, payload: dict) -> StepResult:
        """Parse a wire-format dict into a StepResult."""
        obs_data = payload.get("observation", {})
        return StepResult(
            observation=CloudObservation(
                done=payload.get("done", False),
                reward=payload.get("reward"),
                current_alerts=obs_data.get("current_alerts", []),
                terminal_output=obs_data.get("terminal_output", ""),
                system_health=obs_data.get("system_health", {}),
                available_services=obs_data.get("available_services", []),
                message=obs_data.get("message", ""),
                step_number=obs_data.get("step_number", 0),
                task_progress=obs_data.get("task_progress", 0.0),
            ),
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: dict) -> CloudState:
        """Parse a wire-format dict into a CloudState."""
        return CloudState(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
            task_name=payload.get("task_name", ""),
            task_difficulty=payload.get("task_difficulty", ""),
            total_reward=payload.get("total_reward", 0.0),
            max_steps=payload.get("max_steps", 20),
            services_status=payload.get("services_status", {}),
            incident_resolved=payload.get("incident_resolved", False),
        )
