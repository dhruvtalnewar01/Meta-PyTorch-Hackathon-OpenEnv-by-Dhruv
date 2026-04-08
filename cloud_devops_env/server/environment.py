"""
CloudDevOps-Env: Core Environment Logic
Implements reset(), step(), and state property following the OpenEnv spec.
Simulates an SRE incident debugging environment with deterministic state transitions.
"""

import uuid
import random
from typing import Optional, Dict, Any
from openenv.core.env_server import Environment

# Use relative import for server context, absolute for package context
try:
    from .scenarios import get_scenario, get_all_task_names
except ImportError:
    from scenarios import get_scenario, get_all_task_names

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import CloudAction, CloudObservation, CloudState, CommandType


class CloudDevOpsEnvironment(Environment):
    """
    SRE Incident Debugging Environment.
    
    Simulates realistic cloud infrastructure incidents that an AI agent
    must diagnose and resolve using standard DevOps tooling commands.
    """
    
    SUPPORTS_CONCURRENT_SESSIONS = True
    DEFAULT_TASK = "identify_service_failure"

    def __init__(self):
        self._state = CloudState()
        self._scenario: Dict[str, Any] = {}
        self._action_history: list = []
        self._failed_command_counts: Dict[str, int] = {}
        self._services_stopped: set = set()
        self._fixes_applied: set = set()
        self._current_task: str = self.DEFAULT_TASK
        self._total_reward: float = 0.0
        self._task_progress: float = 0.0

    def reset(self, seed=None, episode_id=None, **kwargs) -> CloudObservation:
        """Initialize a new incident episode."""
        # Allow task selection via kwargs
        task_name = kwargs.get("task", self._current_task)
        if task_name not in get_all_task_names():
            task_name = self.DEFAULT_TASK
        self._current_task = task_name
        
        # Load scenario
        self._scenario = get_scenario(task_name)
        self._action_history = []
        self._failed_command_counts = {}
        self._services_stopped = set()
        self._fixes_applied = set()
        self._total_reward = 0.0
        self._task_progress = 0.0

        # Initialize state
        self._state = CloudState(
            episode_id=episode_id or str(uuid.uuid4()),
            step_count=0,
            task_name=task_name,
            task_difficulty=self._scenario["difficulty"],
            total_reward=0.0,
            max_steps=self._scenario["max_steps"],
            services_status={name: info["status"] for name, info in self._scenario["services"].items()},
            incident_resolved=False,
        )

        return CloudObservation(
            done=False,
            reward=None,
            current_alerts=self._scenario["initial_alerts"],
            terminal_output=f"=== INCIDENT RESPONSE CONSOLE ===\nTask: {self._scenario['description']}\nDifficulty: {self._scenario['difficulty'].upper()}\nAvailable services: {', '.join(self._scenario['services'].keys())}\n\nType commands to investigate and resolve the incident.\nAvailable commands: query_logs, check_metrics, restart_service, scale_service, kill_process, rollback_migration, stop_service, start_service, run_diagnostic, apply_fix, verify_health, wait",
            system_health={name: info["health"] for name, info in self._scenario["services"].items()},
            available_services=list(self._scenario["services"].keys()),
            message=f"INCIDENT ALERT: {self._scenario['description']}",
            step_number=0,
            task_progress=0.0,
        )

    def step(self, action: CloudAction, timeout_s=None, **kwargs) -> CloudObservation:
        """Execute an agent action and return the result."""
        self._state.step_count += 1
        step_num = self._state.step_count
        
        # Track action history
        action_key = f"{action.command.value}:{action.target}"
        self._action_history.append(action_key)
        
        # Check for repeated failed commands (anti-loop penalty)
        step_reward = 0.0
        penalty = 0.0
        terminal_output = ""
        message = ""
        
        # Check if max steps exceeded
        if step_num >= self._scenario["max_steps"]:
            return self._make_done_observation(
                terminal_output="Episode terminated: Maximum steps reached.",
                message="Time's up! The incident was not fully resolved.",
            )
        
        # Check for infinite loop (same failed command 3+ times)
        same_action_count = self._action_history.count(action_key)
        if same_action_count >= 4:
            return self._make_done_observation(
                terminal_output=f"ERROR: Command '{action.command.value} {action.target}' repeated {same_action_count} times. Incident response terminated due to agent loop.",
                message="Episode terminated: Detected infinite loop in agent behavior.",
                penalty=-0.2,
            )
        elif same_action_count >= 3:
            penalty -= 0.05
            terminal_output += f"[WARN] Command repeated {same_action_count} times. Consider a different approach.\n"
        
        # Process the action based on command type
        cmd_result = self._execute_command(action)
        terminal_output += cmd_result["output"]
        step_reward += cmd_result["reward"]
        penalty += cmd_result.get("penalty", 0.0)
        message = cmd_result["message"]
        
        # Update totals
        self._total_reward += step_reward + penalty
        self._total_reward = max(0.0, min(1.0, self._total_reward))  # clamp
        self._state.total_reward = self._total_reward
        
        # Calculate progress
        self._task_progress = self._calculate_progress()
        
        # Check if task is complete
        done = self._check_completion()
        if done:
            self._state.incident_resolved = True
        
        # Update service statuses
        self._state.services_status = {
            name: self._get_service_status(name) 
            for name in self._scenario["services"]
        }

        return CloudObservation(
            done=done,
            reward=step_reward + penalty,
            current_alerts=self._get_current_alerts(),
            terminal_output=terminal_output,
            system_health={name: self._scenario["services"][name]["health"] for name in self._scenario["services"]},
            available_services=list(self._scenario["services"].keys()),
            message=message,
            step_number=step_num,
            task_progress=self._task_progress,
        )

    @property
    def state(self) -> CloudState:
        """Return current episode state."""
        return self._state

    # ========================================================================
    # COMMAND EXECUTION
    # ========================================================================
    
    def _execute_command(self, action: CloudAction) -> Dict[str, Any]:
        """Route command execution to the appropriate handler."""
        handlers = {
            CommandType.QUERY_LOGS: self._handle_query_logs,
            CommandType.CHECK_METRICS: self._handle_check_metrics,
            CommandType.RESTART_SERVICE: self._handle_restart_service,
            CommandType.SCALE_SERVICE: self._handle_scale_service,
            CommandType.KILL_PROCESS: self._handle_kill_process,
            CommandType.ROLLBACK_MIGRATION: self._handle_rollback_migration,
            CommandType.STOP_SERVICE: self._handle_stop_service,
            CommandType.START_SERVICE: self._handle_start_service,
            CommandType.RUN_DIAGNOSTIC: self._handle_run_diagnostic,
            CommandType.APPLY_FIX: self._handle_apply_fix,
            CommandType.VERIFY_HEALTH: self._handle_verify_health,
            CommandType.WAIT: self._handle_wait,
        }
        
        handler = handlers.get(action.command)
        if handler is None:
            return {
                "output": f"ERROR: Unknown command '{action.command}'",
                "reward": 0.0,
                "penalty": -0.02,
                "message": "Invalid command.",
            }
        
        return handler(action)

    def _handle_query_logs(self, action: CloudAction) -> Dict[str, Any]:
        """Query logs for a specific service."""
        target = action.target.strip()
        if not target or target not in self._scenario["services"]:
            return {
                "output": f"ERROR: Service '{target}' not found. Available: {', '.join(self._scenario['services'].keys())}",
                "reward": 0.0,
                "message": f"Service '{target}' does not exist.",
            }
        
        logs = self._scenario["logs"].get(target, ["No logs available."])
        log_output = f"=== LOGS: {target} ===\n" + "\n".join(logs)
        
        # Check if this contributes to finding the problem
        reward = 0.0
        solution = self._scenario["solution"]
        
        if self._current_task == "identify_service_failure":
            if target == solution["target_service"] and not solution["checkpoints"]["identified_failing_service"]:
                solution["checkpoints"]["identified_failing_service"] = True
                reward = 0.3
                log_output += "\n\n[INSIGHT] This service appears to be the source of the problem."
        elif self._current_task == "diagnose_memory_leak":
            if target == solution["target_service"] and not solution["checkpoints"]["identified_leaking_service"]:
                solution["checkpoints"]["identified_leaking_service"] = True
                reward = 0.2
                log_output += "\n\n[INSIGHT] Memory leak pattern detected in this service."
        elif self._current_task == "database_rollback":
            if target == "database" and not solution["checkpoints"]["found_bad_migration"]:
                solution["checkpoints"]["found_bad_migration"] = True
                reward = 0.15
                log_output += "\n\n[INSIGHT] Bad migration identified in the logs."
        
        return {
            "output": log_output,
            "reward": reward,
            "message": f"Retrieved logs for {target}.",
        }

    def _handle_check_metrics(self, action: CloudAction) -> Dict[str, Any]:
        """Check metrics for a specific service."""
        target = action.target.strip()
        if not target or target not in self._scenario["services"]:
            return {
                "output": f"ERROR: Service '{target}' not found.",
                "reward": 0.0,
                "message": f"Service '{target}' does not exist.",
            }
        
        metrics = self._scenario["metrics"].get(target, {})
        service_info = self._scenario["services"][target]
        
        output = f"=== METRICS: {target} ===\n"
        output += f"Status: {service_info['status']} | Health: {service_info['health']}\n"
        output += f"CPU: {service_info['cpu']} | Memory: {service_info['memory']} | Uptime: {service_info['uptime']}\n"
        output += "--- Performance Metrics ---\n"
        for key, value in metrics.items():
            output += f"  {key}: {value}\n"
        
        # Reward for investigating the right service
        reward = 0.0
        solution = self._scenario["solution"]
        
        if self._current_task == "diagnose_memory_leak":
            if target == solution["target_service"] and not solution["checkpoints"]["identified_leaking_service"]:
                solution["checkpoints"]["identified_leaking_service"] = True
                reward = 0.2
            elif target == "cache-service" and solution["checkpoints"]["identified_leaking_service"] and not solution["checkpoints"]["found_leak_source"]:
                solution["checkpoints"]["found_leak_source"] = True
                reward = 0.3
        
        return {
            "output": output,
            "reward": reward,
            "message": f"Metrics retrieved for {target}.",
        }

    def _handle_restart_service(self, action: CloudAction) -> Dict[str, Any]:
        """Restart a service."""
        target = action.target.strip()
        if not target or target not in self._scenario["services"]:
            return {
                "output": f"ERROR: Service '{target}' not found.",
                "reward": 0.0,
                "penalty": -0.05,
                "message": f"Cannot restart unknown service '{target}'.",
            }
        
        solution = self._scenario["solution"]
        reward = 0.0
        
        if self._current_task == "identify_service_failure":
            if target == solution["target_service"]:
                if not solution["checkpoints"]["restarted_service"]:
                    # Check if they diagnosed first
                    if solution["checkpoints"]["diagnosed_root_cause"] or solution["checkpoints"]["identified_failing_service"]:
                        solution["checkpoints"]["restarted_service"] = True
                        self._scenario["services"][target]["status"] = "running"
                        self._scenario["services"][target]["health"] = "healthy"
                        reward = 0.3
                        return {
                            "output": f"Service '{target}' restarted successfully.\n[OK] Service is now healthy and accepting requests.",
                            "reward": reward,
                            "message": f"Successfully restarted {target}!",
                        }
                    else:
                        # Restarted without diagnosing — partial credit
                        solution["checkpoints"]["restarted_service"] = True
                        self._scenario["services"][target]["status"] = "running"
                        self._scenario["services"][target]["health"] = "healthy"
                        reward = 0.15  # Less reward for blind restart
                        return {
                            "output": f"Service '{target}' restarted successfully.\n[WARN] Service restarted without root cause analysis. Issue may recur.",
                            "reward": reward,
                            "message": f"Restarted {target} but root cause unknown.",
                        }
            else:
                return {
                    "output": f"Service '{target}' restarted. No effect on the incident.",
                    "reward": 0.0,
                    "penalty": -0.05,
                    "message": f"Restarting {target} did not help.",
                }
        
        # Generic restart for other tasks
        self._scenario["services"][target]["status"] = "running"
        self._scenario["services"][target]["health"] = "healthy"
        return {
            "output": f"Service '{target}' restarted.",
            "reward": reward,
            "message": f"Restarted {target}.",
        }

    def _handle_run_diagnostic(self, action: CloudAction) -> Dict[str, Any]:
        """Run diagnostics on a service."""
        target = action.target.strip()
        if not target or target not in self._scenario["services"]:
            return {
                "output": f"ERROR: Service '{target}' not found.",
                "reward": 0.0,
                "message": f"Service '{target}' does not exist.",
            }
        
        diag = self._scenario["diagnostics"].get(target, "No diagnostic data available.")
        output = f"=== DIAGNOSTIC REPORT: {target} ===\n{diag}"
        
        reward = 0.0
        solution = self._scenario["solution"]
        
        if self._current_task == "identify_service_failure":
            if target == solution["target_service"] and not solution["checkpoints"]["diagnosed_root_cause"]:
                solution["checkpoints"]["diagnosed_root_cause"] = True
                reward = 0.4
                output += "\n\n[ROOT CAUSE IDENTIFIED] OOM - Java heap space exhaustion during batch sync."
        elif self._current_task == "diagnose_memory_leak":
            if target == solution["target_service"] and not solution["checkpoints"]["found_leak_source"]:
                solution["checkpoints"]["found_leak_source"] = True
                reward = 0.3
                output += "\n\n[LEAK SOURCE IDENTIFIED] Session cache storing objects without TTL."
        elif self._current_task == "database_rollback":
            if target == "database" and not solution["checkpoints"]["found_bad_migration"]:
                solution["checkpoints"]["found_bad_migration"] = True
                reward = 0.15
                output += "\n\n[BAD MIGRATION IDENTIFIED] v2.8.0_add_payment_fields"
        
        return {
            "output": output,
            "reward": reward,
            "message": f"Diagnostic complete for {target}.",
        }

    def _handle_stop_service(self, action: CloudAction) -> Dict[str, Any]:
        """Stop a service."""
        target = action.target.strip()
        if not target or target not in self._scenario["services"]:
            return {
                "output": f"ERROR: Service '{target}' not found.",
                "reward": 0.0,
                "penalty": -0.05,
                "message": f"Cannot stop unknown service '{target}'.",
            }
        
        reward = 0.0
        solution = self._scenario["solution"]
        
        self._scenario["services"][target]["status"] = "stopped"
        self._scenario["services"][target]["health"] = "stopped"
        self._services_stopped.add(target)
        
        if self._current_task == "database_rollback":
            services_to_stop = set(solution["services_to_stop"])
            if target in services_to_stop:
                if services_to_stop.issubset(self._services_stopped):
                    if not solution["checkpoints"]["stopped_dependent_services"]:
                        solution["checkpoints"]["stopped_dependent_services"] = True
                        reward = 0.15
                        return {
                            "output": f"Service '{target}' stopped.\n[OK] All dependent services are now stopped. Safe to proceed with rollback.",
                            "reward": reward,
                            "message": "All dependent services stopped. Ready for rollback.",
                        }
                return {
                    "output": f"Service '{target}' stopped successfully. Need to also stop: {', '.join(services_to_stop - self._services_stopped)}",
                    "reward": 0.0,
                    "message": f"Stopped {target}. Other dependent services still running.",
                }
            else:
                return {
                    "output": f"Service '{target}' stopped. WARNING: This service is not a dependency of the bad migration.",
                    "reward": 0.0,
                    "penalty": -0.05,
                    "message": f"Stopped {target} unnecessarily.",
                }
        
        return {
            "output": f"Service '{target}' stopped.",
            "reward": reward,
            "message": f"Stopped {target}.",
        }

    def _handle_start_service(self, action: CloudAction) -> Dict[str, Any]:
        """Start a previously stopped service."""
        target = action.target.strip()
        if not target or target not in self._scenario["services"]:
            return {
                "output": f"ERROR: Service '{target}' not found.",
                "reward": 0.0,
                "message": f"Service '{target}' does not exist.",
            }
        
        solution = self._scenario["solution"]
        reward = 0.0
        
        self._scenario["services"][target]["status"] = "running"
        self._scenario["services"][target]["health"] = "healthy"
        
        if self._current_task == "database_rollback":
            if target in solution.get("services_to_stop", []):
                if solution["checkpoints"].get("executed_rollback", False):
                    self._services_stopped.discard(target)
                    services_to_restart = set(solution["services_to_stop"])
                    still_stopped = services_to_restart.intersection(self._services_stopped)
                    if not still_stopped and not solution["checkpoints"]["restarted_services"]:
                        solution["checkpoints"]["restarted_services"] = True
                        reward = 0.20
                        return {
                            "output": f"Service '{target}' started.\n[OK] All dependent services restarted successfully.",
                            "reward": reward,
                            "message": "All services restarted after rollback.",
                        }
                    return {
                        "output": f"Service '{target}' started successfully.",
                        "reward": 0.0,
                        "message": f"Started {target}. Other services still need restart: {', '.join(still_stopped)}" if still_stopped else f"Started {target}.",
                    }
                else:
                    return {
                        "output": f"WARNING: Starting {target} before rollback is complete! This may cause further data corruption.",
                        "reward": 0.0,
                        "penalty": -0.1,
                        "message": "Started service before rollback — risk of data corruption!",
                    }
        
        return {
            "output": f"Service '{target}' started.",
            "reward": reward,
            "message": f"Started {target}.",
        }

    def _handle_rollback_migration(self, action: CloudAction) -> Dict[str, Any]:
        """Rollback a database migration."""
        target = action.target.strip()  # migration ID
        solution = self._scenario["solution"]
        
        if self._current_task != "database_rollback":
            return {
                "output": "ERROR: No migrations to rollback in this scenario.",
                "reward": 0.0,
                "penalty": -0.05,
                "message": "This command is not applicable to the current incident.",
            }
        
        if target != solution["bad_migration"]:
            return {
                "output": f"ERROR: Migration '{target}' is not the problematic migration. Check logs for the correct migration ID.",
                "reward": 0.0,
                "penalty": -0.1,
                "message": f"Wrong migration target: {target}",
            }
        
        # Check if dependent services are stopped
        services_to_stop = set(solution["services_to_stop"])
        if not services_to_stop.issubset(self._services_stopped):
            running = services_to_stop - self._services_stopped
            return {
                "output": f"DANGER: Cannot safely rollback while dependent services are running: {', '.join(running)}.\nStop these services first to prevent data corruption during rollback.",
                "reward": 0.0,
                "penalty": -0.1,
                "message": "Cannot rollback: dependent services still running!",
            }
        
        # Execute rollback
        if not solution["checkpoints"]["executed_rollback"]:
            solution["checkpoints"]["executed_rollback"] = True
            # Fix database state
            self._scenario["services"]["database"]["health"] = "healthy"
            self._scenario["services"]["database"]["cpu"] = "35%"
            return {
                "output": f"=== MIGRATION ROLLBACK ===\nRolling back: {target}\nExecuting: ALTER TABLE orders DROP COLUMN payment_method_id;\nExecuting: ALTER TABLE orders DROP COLUMN payment_processor;\n[OK] Migration {target} rolled back successfully.\n[OK] Data integrity restored for 450,000 order records.\n[OK] Database health: HEALTHY",
                "reward": 0.30,
                "message": "Database migration rolled back successfully!",
            }
        else:
            return {
                "output": f"Migration {target} has already been rolled back.",
                "reward": 0.0,
                "message": "Already rolled back.",
            }

    def _handle_kill_process(self, action: CloudAction) -> Dict[str, Any]:
        """Kill a specific process."""
        target = action.target.strip()
        solution = self._scenario["solution"]
        reward = 0.0
        
        if self._current_task == "diagnose_memory_leak":
            if target == solution["target_service"] or target == "session-cache":
                if solution["checkpoints"].get("found_leak_source", False):
                    return {
                        "output": f"Process for '{target}' killed.\n[OK] Memory-leaking process terminated. Cache cleared.",
                        "reward": 0.0,  # Reward comes from apply_fix
                        "message": f"Killed {target} process.",
                    }
                return {
                    "output": f"Process '{target}' killed without diagnosis.",
                    "reward": 0.0,
                    "penalty": -0.05,
                    "message": "Killed process without understanding root cause.",
                }
        
        return {
            "output": f"Process '{target}' killed.",
            "reward": reward,
            "message": f"Killed {target}.",
        }

    def _handle_apply_fix(self, action: CloudAction) -> Dict[str, Any]:
        """Apply a fix to a service or component."""
        target = action.target.strip()
        fix_type = action.args.get("fix", "")
        solution = self._scenario["solution"]
        
        if self._current_task == "diagnose_memory_leak":
            if target == solution["target_service"] or "cache" in target.lower() or "ttl" in fix_type.lower() or "session" in target.lower():
                if not solution["checkpoints"]["applied_fix"]:
                    solution["checkpoints"]["applied_fix"] = True
                    self._fixes_applied.add(target)
                    self._scenario["services"]["payment-service"]["memory"] = "350MB"
                    self._scenario["services"]["payment-service"]["health"] = "healthy"
                    self._scenario["services"]["payment-service"]["cpu"] = "15%"
                    return {
                        "output": f"=== FIX APPLIED ===\nTarget: {target}\nAction: Applied TTL to session cache entries, cleared stale sessions.\n[OK] 120,000 stale session entries purged.\n[OK] Memory usage dropped from 1800MB to 350MB.\n[OK] Redis connection pool: 50/500 connections.\n[OK] Service health: HEALTHY",
                        "reward": 0.2,
                        "message": "Fix applied successfully! Memory leak resolved.",
                    }
            return {
                "output": f"Fix applied to '{target}' but no improvement observed.",
                "reward": 0.0,
                "penalty": -0.05,
                "message": f"Fix on {target} had no effect.",
            }
        
        return {
            "output": f"Fix applied to '{target}'.",
            "reward": 0.0,
            "message": f"Applied fix to {target}.",
        }

    def _handle_verify_health(self, action: CloudAction) -> Dict[str, Any]:
        """Verify system health after fixes."""
        solution = self._scenario["solution"]
        
        if self._current_task == "diagnose_memory_leak":
            if solution["checkpoints"].get("applied_fix", False):
                if not solution["checkpoints"]["verified_fix"]:
                    solution["checkpoints"]["verified_fix"] = True
                    return {
                        "output": "=== HEALTH VERIFICATION ===\nAll services: HEALTHY\npayment-service: Memory stable at 350MB, no growth detected.\nCache: 5,000 entries with proper TTL.\nError rate: 0%\n[OK] Incident resolved. All systems operational.",
                        "reward": 0.3,
                        "message": "Health verified. Incident fully resolved!",
                    }
                return {
                    "output": "Health already verified. All systems operational.",
                    "reward": 0.0,
                    "message": "Already verified.",
                }
            return {
                "output": "=== HEALTH VERIFICATION ===\nWARNING: Issues still detected.\npayment-service memory still growing. Fix not yet applied.",
                "reward": 0.0,
                "message": "Health check failed — issues remain.",
            }
        elif self._current_task == "database_rollback":
            if solution["checkpoints"].get("restarted_services", False):
                if not solution["checkpoints"]["verified_health"]:
                    solution["checkpoints"]["verified_health"] = True
                    return {
                        "output": "=== HEALTH VERIFICATION ===\nDatabase: HEALTHY - No integrity errors\norder-service: HEALTHY - Processing orders\npayment-service: HEALTHY - Processing payments\nError rate: 0%\n[OK] All systems operational. Incident resolved.",
                        "reward": 0.20,
                        "message": "Health verified. Incident fully resolved!",
                    }
                return {
                    "output": "Health already verified.",
                    "reward": 0.0,
                    "message": "Already verified.",
                }
            elif solution["checkpoints"].get("executed_rollback", False):
                return {
                    "output": "=== HEALTH VERIFICATION ===\nDatabase: HEALTHY\norder-service: STOPPED - needs restart\npayment-service: STOPPED - needs restart\n[WARN] Dependent services need to be restarted.",
                    "reward": 0.0,
                    "message": "Services still need restart.",
                }
            return {
                "output": "=== HEALTH VERIFICATION ===\nCRITICAL: Issues still active.\nDatabase integrity errors persist. Rollback not yet completed.",
                "reward": 0.0,
                "message": "Health check failed — rollback needed.",
            }
        else:  # identify_service_failure
            if solution["checkpoints"].get("restarted_service", False):
                return {
                    "output": "=== HEALTH VERIFICATION ===\nAll services: HEALTHY\nuser-service: Running, processing requests normally.\nError rate: 0%\n[OK] Incident resolved.",
                    "reward": 0.0,  # Already got reward for restart
                    "message": "All systems healthy.",
                }
            return {
                "output": "=== HEALTH VERIFICATION ===\nWARNING: user-service still down.\n[FAIL] Incident not resolved.",
                "reward": 0.0,
                "message": "Health check failed.",
            }

    def _handle_scale_service(self, action: CloudAction) -> Dict[str, Any]:
        """Scale a service (not typically the right action for these incidents)."""
        target = action.target.strip()
        return {
            "output": f"Service '{target}' scaled. Note: scaling does not fix underlying issues like OOM, memory leaks, or bad migrations.",
            "reward": 0.0,
            "penalty": -0.02,
            "message": f"Scaled {target} — but this doesn't address the root cause.",
        }

    def _handle_wait(self, action: CloudAction) -> Dict[str, Any]:
        """Wait and observe — wastes a step but no penalty."""
        return {
            "output": "Waiting... System state unchanged.",
            "reward": 0.0,
            "message": "Waited one cycle. No changes observed.",
        }

    # ========================================================================
    # HELPERS
    # ========================================================================
    
    def _calculate_progress(self) -> float:
        """Calculate task completion progress."""
        solution = self._scenario["solution"]
        checkpoints = solution["checkpoints"]
        completed = sum(1 for v in checkpoints.values() if v)
        total = len(checkpoints)
        return completed / total if total > 0 else 0.0

    def _check_completion(self) -> bool:
        """Check if all checkpoints are completed."""
        solution = self._scenario["solution"]
        return all(solution["checkpoints"].values())

    def _get_current_alerts(self) -> list:
        """Get current alerts based on state."""
        solution = self._scenario["solution"]
        alerts = []
        
        if not all(solution["checkpoints"].values()):
            alerts = [a for a in self._scenario["initial_alerts"]]
            # Remove alerts for resolved issues
            if self._current_task == "identify_service_failure":
                if solution["checkpoints"].get("restarted_service", False):
                    alerts = ["[RESOLVED] Service failure incident resolved."]
            elif self._current_task == "diagnose_memory_leak":
                if solution["checkpoints"].get("verified_fix", False):
                    alerts = ["[RESOLVED] Memory leak incident resolved."]
            elif self._current_task == "database_rollback":
                if solution["checkpoints"].get("verified_health", False):
                    alerts = ["[RESOLVED] Database rollback incident resolved."]
        else:
            alerts = ["[RESOLVED] All incidents resolved. Systems healthy."]
        
        return alerts

    def _get_service_status(self, name: str) -> str:
        """Get current status of a service."""
        return self._scenario["services"][name]["status"]

    def _make_done_observation(self, terminal_output: str, message: str, penalty: float = 0.0) -> CloudObservation:
        """Create a terminal observation (episode end)."""
        self._total_reward += penalty
        self._total_reward = max(0.0, min(1.0, self._total_reward))
        self._state.total_reward = self._total_reward
        
        return CloudObservation(
            done=True,
            reward=penalty,
            current_alerts=["INCIDENT RESPONSE TERMINATED"],
            terminal_output=terminal_output,
            system_health={name: self._scenario["services"][name]["health"] for name in self._scenario["services"]},
            available_services=list(self._scenario["services"].keys()),
            message=message,
            step_number=self._state.step_count,
            task_progress=self._task_progress,
        )
