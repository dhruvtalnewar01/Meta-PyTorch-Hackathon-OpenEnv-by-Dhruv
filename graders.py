"""
CloudDevOps-Env: Task Graders
Deterministic graders for 3 tasks. Each grader analyzes the trajectory
of actions and final system state, returning a score in [0.0, 1.0].
"""

from typing import List, Dict, Any


class BaseGrader:
    """Base class for task graders."""
    
    def grade(self, trajectory: List[Dict[str, Any]], final_state: Dict[str, Any]) -> float:
        """
        Grade an episode.
        
        Args:
            trajectory: List of step records, each with:
                - action: dict with command, target, args
                - observation: dict with terminal_output, message, etc.
                - reward: float
                - done: bool
            final_state: The final CloudState as a dict
        
        Returns:
            Score between 0.0 and 1.0
        """
        raise NotImplementedError


class IdentifyServiceFailureGrader(BaseGrader):
    """
    EASY — Grader for Task 1: Identify Service Failure
    
    Scoring:
    - 0.30: Identified the failing service (user-service)
    - 0.40: Diagnosed root cause (OOM / Java heap)
    - 0.30: Restarted the correct service
    
    Penalties:
    - -0.05 per unnecessary restart of a healthy service
    - -0.10 if agent loops (same failed command 3+ times)
    """
    
    TASK_NAME = "identify_service_failure"
    TARGET_SERVICE = "user-service"
    
    def grade(self, trajectory: List[Dict[str, Any]], final_state: Dict[str, Any]) -> float:
        score = 0.0
        penalties = 0.0
        
        identified_service = False
        diagnosed_cause = False
        restarted_service = False
        unnecessary_restarts = 0
        command_counts: Dict[str, int] = {}
        
        for step in trajectory:
            action = step.get("action", {})
            cmd = action.get("command", "")
            target = action.get("target", "")
            output = step.get("observation", {}).get("terminal_output", "")
            
            # Track command repetitions
            action_key = f"{cmd}:{target}"
            command_counts[action_key] = command_counts.get(action_key, 0) + 1
            
            # Check for identification
            if cmd in ("query_logs", "check_metrics", "run_diagnostic") and target == self.TARGET_SERVICE:
                identified_service = True
            
            # Check for diagnosis (looked at diagnostic or detailed logs)
            if cmd == "run_diagnostic" and target == self.TARGET_SERVICE:
                diagnosed_cause = True
            elif cmd == "query_logs" and target == self.TARGET_SERVICE:
                if "OOM" in output or "OutOfMemory" in output or "heap" in output.lower():
                    diagnosed_cause = True
            
            # Check for restart
            if cmd == "restart_service" and target == self.TARGET_SERVICE:
                restarted_service = True
            elif cmd == "restart_service" and target != self.TARGET_SERVICE:
                unnecessary_restarts += 1
        
        # Calculate score
        if identified_service:
            score += 0.30
        if diagnosed_cause:
            score += 0.40
        if restarted_service:
            score += 0.30
        
        # Apply penalties
        penalties -= unnecessary_restarts * 0.05
        
        # Check for loops
        for key, count in command_counts.items():
            if count >= 4:
                penalties -= 0.10
                break
        
        final_score = max(0.0, min(1.0, score + penalties))
        return round(final_score, 2)


class DiagnoseMemoryLeakGrader(BaseGrader):
    """
    MEDIUM — Grader for Task 2: Diagnose Memory Leak
    
    Scoring:
    - 0.20: Identified the leaking service (payment-service)
    - 0.30: Found the leak source (session cache / no TTL)
    - 0.20: Applied the fix (clear cache, set TTL)
    - 0.30: Verified the fix (health check passed)
    
    Penalties:
    - -0.05 per unnecessary service kill
    - -0.05 for blind restarts without diagnosis
    """
    
    TASK_NAME = "diagnose_memory_leak"
    TARGET_SERVICE = "payment-service"
    LEAK_KEYWORDS = ["session", "cache", "ttl", "no ttl", "no_ttl", "stale"]
    
    def grade(self, trajectory: List[Dict[str, Any]], final_state: Dict[str, Any]) -> float:
        score = 0.0
        penalties = 0.0
        
        identified_service = False
        found_leak_source = False
        applied_fix = False
        verified_fix = False
        
        for step in trajectory:
            action = step.get("action", {})
            cmd = action.get("command", "")
            target = action.get("target", "")
            output = step.get("observation", {}).get("terminal_output", "").lower()
            
            # Check for identification
            if cmd in ("query_logs", "check_metrics", "run_diagnostic") and target == self.TARGET_SERVICE:
                identified_service = True
            
            # Check for leak source discovery
            if cmd in ("query_logs", "check_metrics", "run_diagnostic"):
                if any(kw in output for kw in self.LEAK_KEYWORDS):
                    found_leak_source = True
                if target == "cache-service":
                    found_leak_source = True
            
            # Check for fix application
            if cmd == "apply_fix":
                if target == self.TARGET_SERVICE or "cache" in target.lower() or "session" in target.lower():
                    if "fix applied" in output or "purged" in output or "resolved" in output:
                        applied_fix = True
            
            # Check for verification
            if cmd == "verify_health":
                if "resolved" in output or "healthy" in output:
                    verified_fix = True
            
            # Penalties for blind actions
            if cmd == "restart_service" and not found_leak_source:
                penalties -= 0.05
        
        if identified_service:
            score += 0.20
        if found_leak_source:
            score += 0.30
        if applied_fix:
            score += 0.20
        if verified_fix:
            score += 0.30
        
        final_score = max(0.0, min(1.0, score + penalties))
        return round(final_score, 2)


class DatabaseRollbackGrader(BaseGrader):
    """
    HARD — Grader for Task 3: Database Rollback Under Pressure
    
    Scoring:
    - 0.15: Found the bad migration (v2.8.0_add_payment_fields)
    - 0.15: Stopped dependent services (order-service, payment-service)
    - 0.30: Executed the rollback successfully
    - 0.20: Restarted services after rollback
    - 0.20: Verified system health
    
    Penalties:
    - -0.10 for attempting rollback without stopping services
    - -0.10 for rolling back the wrong migration
    - -0.05 for starting services before rollback completes
    """
    
    TASK_NAME = "database_rollback"
    BAD_MIGRATION = "v2.8.0_add_payment_fields"
    SERVICES_TO_STOP = {"order-service", "payment-service"}
    
    def grade(self, trajectory: List[Dict[str, Any]], final_state: Dict[str, Any]) -> float:
        score = 0.0
        penalties = 0.0
        
        found_migration = False
        stopped_services = set()
        rollback_executed = False
        services_restarted = set()
        health_verified = False
        rollback_before_stop = False
        started_before_rollback = False
        
        for step in trajectory:
            action = step.get("action", {})
            cmd = action.get("command", "")
            target = action.get("target", "")
            output = step.get("observation", {}).get("terminal_output", "").lower()
            
            # Check for migration identification
            if cmd in ("query_logs", "run_diagnostic") and target == "database":
                if self.BAD_MIGRATION.lower() in output or "bad migration" in output:
                    found_migration = True
            
            # Track service stops
            if cmd == "stop_service" and target in self.SERVICES_TO_STOP:
                stopped_services.add(target)
            
            # Check for rollback
            if cmd == "rollback_migration":
                if target == self.BAD_MIGRATION:
                    if self.SERVICES_TO_STOP.issubset(stopped_services):
                        rollback_executed = True
                    else:
                        rollback_before_stop = True
                else:
                    penalties -= 0.10  # Wrong migration
            
            # Check for service restart after rollback
            if cmd == "start_service" and target in self.SERVICES_TO_STOP:
                if rollback_executed:
                    services_restarted.add(target)
                else:
                    started_before_rollback = True
            
            # Check for health verification
            if cmd == "verify_health":
                if rollback_executed and self.SERVICES_TO_STOP.issubset(services_restarted):
                    if "resolved" in output or "healthy" in output or "operational" in output:
                        health_verified = True
        
        if found_migration:
            score += 0.15
        if self.SERVICES_TO_STOP.issubset(stopped_services):
            score += 0.15
        if rollback_executed:
            score += 0.30
        if self.SERVICES_TO_STOP.issubset(services_restarted) and rollback_executed:
            score += 0.20
        if health_verified:
            score += 0.20
        
        # Penalties
        if rollback_before_stop:
            penalties -= 0.10
        if started_before_rollback:
            penalties -= 0.05
        
        final_score = max(0.0, min(1.0, score + penalties))
        return round(final_score, 2)


# ============================================================================
# Grader Registry
# ============================================================================

GRADERS = {
    "identify_service_failure": IdentifyServiceFailureGrader(),
    "diagnose_memory_leak": DiagnoseMemoryLeakGrader(),
    "database_rollback": DatabaseRollbackGrader(),
}


def grade_task(task_name: str, trajectory: List[Dict[str, Any]], final_state: Dict[str, Any]) -> float:
    """
    Grade a task by name.
    
    Args:
        task_name: One of the registered task names
        trajectory: List of step records
        final_state: Final environment state dict
    
    Returns:
        Score between 0.0 and 1.0
    """
    if task_name not in GRADERS:
        raise ValueError(f"Unknown task: {task_name}. Available: {list(GRADERS.keys())}")
    return GRADERS[task_name].grade(trajectory, final_state)
