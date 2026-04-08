"""Quick smoke test to verify the CloudDevOps environment works correctly."""
import sys
import os

# Add paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import CloudAction, CommandType
from server.environment import CloudDevOpsEnvironment
from graders import grade_task

def test_task_1():
    """Test Easy task: Identify Service Failure"""
    print("=" * 60)
    print("TASK 1: Identify Service Failure (Easy)")
    print("=" * 60)
    
    env = CloudDevOpsEnvironment()
    result = env.reset(task="identify_service_failure")
    print(f"  Reset OK | Alerts: {len(result.current_alerts)} | Services: {len(result.available_services)}")
    assert not result.done
    
    trajectory = []
    
    # Step 1: Query logs for user-service
    action = CloudAction(command=CommandType.QUERY_LOGS, target="user-service")
    result = env.step(action)
    trajectory.append({"action": {"command": "query_logs", "target": "user-service"}, "observation": {"terminal_output": result.terminal_output, "message": result.message}, "reward": result.reward, "done": result.done})
    print(f"  Step 1: query_logs user-service | reward={result.reward} | progress={result.task_progress:.0%}")
    
    # Step 2: Run diagnostic
    action = CloudAction(command=CommandType.RUN_DIAGNOSTIC, target="user-service")
    result = env.step(action)
    trajectory.append({"action": {"command": "run_diagnostic", "target": "user-service"}, "observation": {"terminal_output": result.terminal_output, "message": result.message}, "reward": result.reward, "done": result.done})
    print(f"  Step 2: run_diagnostic user-service | reward={result.reward} | progress={result.task_progress:.0%}")
    
    # Step 3: Restart service
    action = CloudAction(command=CommandType.RESTART_SERVICE, target="user-service")
    result = env.step(action)
    trajectory.append({"action": {"command": "restart_service", "target": "user-service"}, "observation": {"terminal_output": result.terminal_output, "message": result.message}, "reward": result.reward, "done": result.done})
    print(f"  Step 3: restart_service user-service | reward={result.reward} | done={result.done}")
    
    # Grade
    score = grade_task("identify_service_failure", trajectory, {})
    print(f"  GRADER SCORE: {score}")
    assert 0.0 <= score <= 1.0, f"Score out of range: {score}"
    assert score >= 0.9, f"Expected near-perfect score, got {score}"
    print(f"  ✅ Task 1 PASSED (score={score})")
    return score


def test_task_2():
    """Test Medium task: Diagnose Memory Leak"""
    print("\n" + "=" * 60)
    print("TASK 2: Diagnose Memory Leak (Medium)")
    print("=" * 60)
    
    env = CloudDevOpsEnvironment()
    result = env.reset(task="diagnose_memory_leak")
    print(f"  Reset OK | Alerts: {len(result.current_alerts)}")
    
    trajectory = []
    
    # Step 1: Check metrics for payment-service
    action = CloudAction(command=CommandType.CHECK_METRICS, target="payment-service")
    result = env.step(action)
    trajectory.append({"action": {"command": "check_metrics", "target": "payment-service"}, "observation": {"terminal_output": result.terminal_output, "message": result.message}, "reward": result.reward, "done": result.done})
    print(f"  Step 1: check_metrics payment-service | reward={result.reward}")
    
    # Step 2: Run diagnostic
    action = CloudAction(command=CommandType.RUN_DIAGNOSTIC, target="payment-service")
    result = env.step(action)
    trajectory.append({"action": {"command": "run_diagnostic", "target": "payment-service"}, "observation": {"terminal_output": result.terminal_output, "message": result.message}, "reward": result.reward, "done": result.done})
    print(f"  Step 2: run_diagnostic payment-service | reward={result.reward}")
    
    # Step 3: Apply fix
    action = CloudAction(command=CommandType.APPLY_FIX, target="payment-service", args={"fix": "set_ttl"})
    result = env.step(action)
    trajectory.append({"action": {"command": "apply_fix", "target": "payment-service"}, "observation": {"terminal_output": result.terminal_output, "message": result.message}, "reward": result.reward, "done": result.done})
    print(f"  Step 3: apply_fix payment-service | reward={result.reward}")
    
    # Step 4: Verify health
    action = CloudAction(command=CommandType.VERIFY_HEALTH, target="")
    result = env.step(action)
    trajectory.append({"action": {"command": "verify_health", "target": ""}, "observation": {"terminal_output": result.terminal_output, "message": result.message}, "reward": result.reward, "done": result.done})
    print(f"  Step 4: verify_health | reward={result.reward} | done={result.done}")
    
    score = grade_task("diagnose_memory_leak", trajectory, {})
    print(f"  GRADER SCORE: {score}")
    assert 0.0 <= score <= 1.0
    assert score >= 0.9, f"Expected near-perfect score, got {score}"
    print(f"  ✅ Task 2 PASSED (score={score})")
    return score


def test_task_3():
    """Test Hard task: Database Rollback"""
    print("\n" + "=" * 60)
    print("TASK 3: Database Rollback Under Pressure (Hard)")
    print("=" * 60)
    
    env = CloudDevOpsEnvironment()
    result = env.reset(task="database_rollback")
    print(f"  Reset OK | Alerts: {len(result.current_alerts)}")
    
    trajectory = []
    
    # Step 1: Query database logs
    action = CloudAction(command=CommandType.QUERY_LOGS, target="database")
    result = env.step(action)
    trajectory.append({"action": {"command": "query_logs", "target": "database"}, "observation": {"terminal_output": result.terminal_output, "message": result.message}, "reward": result.reward, "done": result.done})
    print(f"  Step 1: query_logs database | reward={result.reward}")
    
    # Step 2: Stop order-service
    action = CloudAction(command=CommandType.STOP_SERVICE, target="order-service")
    result = env.step(action)
    trajectory.append({"action": {"command": "stop_service", "target": "order-service"}, "observation": {"terminal_output": result.terminal_output, "message": result.message}, "reward": result.reward, "done": result.done})
    print(f"  Step 2: stop_service order-service | reward={result.reward}")
    
    # Step 3: Stop payment-service
    action = CloudAction(command=CommandType.STOP_SERVICE, target="payment-service")
    result = env.step(action)
    trajectory.append({"action": {"command": "stop_service", "target": "payment-service"}, "observation": {"terminal_output": result.terminal_output, "message": result.message}, "reward": result.reward, "done": result.done})
    print(f"  Step 3: stop_service payment-service | reward={result.reward}")
    
    # Step 4: Rollback migration
    action = CloudAction(command=CommandType.ROLLBACK_MIGRATION, target="v2.8.0_add_payment_fields")
    result = env.step(action)
    trajectory.append({"action": {"command": "rollback_migration", "target": "v2.8.0_add_payment_fields"}, "observation": {"terminal_output": result.terminal_output, "message": result.message}, "reward": result.reward, "done": result.done})
    print(f"  Step 4: rollback_migration | reward={result.reward}")
    
    # Step 5: Start order-service
    action = CloudAction(command=CommandType.START_SERVICE, target="order-service")
    result = env.step(action)
    trajectory.append({"action": {"command": "start_service", "target": "order-service"}, "observation": {"terminal_output": result.terminal_output, "message": result.message}, "reward": result.reward, "done": result.done})
    print(f"  Step 5: start_service order-service | reward={result.reward}")
    
    # Step 6: Start payment-service
    action = CloudAction(command=CommandType.START_SERVICE, target="payment-service")
    result = env.step(action)
    trajectory.append({"action": {"command": "start_service", "target": "payment-service"}, "observation": {"terminal_output": result.terminal_output, "message": result.message}, "reward": result.reward, "done": result.done})
    print(f"  Step 6: start_service payment-service | reward={result.reward}")
    
    # Step 7: Verify health
    action = CloudAction(command=CommandType.VERIFY_HEALTH, target="")
    result = env.step(action)
    trajectory.append({"action": {"command": "verify_health", "target": ""}, "observation": {"terminal_output": result.terminal_output, "message": result.message}, "reward": result.reward, "done": result.done})
    print(f"  Step 7: verify_health | reward={result.reward} | done={result.done}")
    
    score = grade_task("database_rollback", trajectory, {})
    print(f"  GRADER SCORE: {score}")
    assert 0.0 <= score <= 1.0
    assert score >= 0.9, f"Expected near-perfect score, got {score}"
    print(f"  ✅ Task 3 PASSED (score={score})")
    return score


if __name__ == "__main__":
    print("🔧 CloudDevOps-Env Smoke Test")
    print("=" * 60)
    
    s1 = test_task_1()
    s2 = test_task_2()
    s3 = test_task_3()
    
    print("\n" + "=" * 60)
    print(f"ALL TESTS PASSED ✅")
    print(f"  Easy:   {s1:.2f}")
    print(f"  Medium: {s2:.2f}")  
    print(f"  Hard:   {s3:.2f}")
    print(f"  Avg:    {(s1+s2+s3)/3:.2f}")
    print("=" * 60)
