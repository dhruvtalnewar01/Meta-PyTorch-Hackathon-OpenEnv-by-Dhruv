"""
CloudDevOps-Env: Baseline Inference Script

Uses the OpenAI API client to run a model against the CloudDevOps environment.
Reads credentials from environment variables.
Produces structured stdout logs in [START], [STEP], [END] format.

CRITICAL: This script follows the exact structured logging format required
by the hackathon evaluation system. Do not modify the log format.
"""

import os
import sys
import json
import asyncio
from typing import List, Dict, Any, Optional

from openai import OpenAI

# ============================================================================
# ENVIRONMENT VARIABLES (mandatory)
# ============================================================================
API_BASE_URL = os.getenv("API_BASE_URL", "<your-active-api-base-url>")
MODEL_NAME = os.getenv("MODEL_NAME", "<your-active-model-name>")
HF_TOKEN = os.getenv("HF_TOKEN")

# Optional — if using from_docker_image()
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")

# ============================================================================
# CONFIGURATION
# ============================================================================
BENCHMARK = "cloud_devops_env"
MAX_STEPS = 20
SUCCESS_SCORE_THRESHOLD = 0.6

TASKS = [
    {"name": "identify_service_failure", "difficulty": "easy", "max_steps": 10},
    {"name": "diagnose_memory_leak", "difficulty": "medium", "max_steps": 15},
    {"name": "database_rollback", "difficulty": "hard", "max_steps": 20},
]

# ============================================================================
# STRUCTURED LOGGING — [START], [STEP], [END]
# CRITICAL: Do NOT modify field names, ordering, or formatting.
# ============================================================================

def log_start(task: str, env: str, model: str) -> None:
    """Emit [START] log."""
    payload = {
        "task": task,
        "env": env,
        "model": model,
    }
    print(f"[START] {json.dumps(payload)}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str] = None) -> None:
    """Emit [STEP] log."""
    payload = {
        "step": step,
        "action": action,
        "reward": reward,
        "done": done,
        "error": error,
    }
    print(f"[STEP] {json.dumps(payload)}", flush=True)


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    """Emit [END] log."""
    payload = {
        "success": success,
        "steps": steps,
        "score": score,
        "rewards": rewards,
    }
    print(f"[END] {json.dumps(payload)}", flush=True)


# ============================================================================
# LLM-BASED AGENT
# ============================================================================

SYSTEM_PROMPT = """You are an expert Site Reliability Engineer (SRE) debugging a production incident.
You have access to the following commands:
- query_logs <service_name> — View logs for a service
- check_metrics <service_name> — Check performance metrics
- restart_service <service_name> — Restart a service
- stop_service <service_name> — Stop a service  
- start_service <service_name> — Start a stopped service
- run_diagnostic <service_name> — Run diagnostics
- kill_process <target> — Kill a process
- rollback_migration <migration_id> — Rollback a database migration
- apply_fix <target> — Apply a fix (include fix details in args)
- verify_health — Verify overall system health
- wait — Wait and observe

Respond with EXACTLY one command per step in this JSON format:
{"command": "<command_type>", "target": "<target>", "args": {}}

Strategy:
1. First, investigate by querying logs and checking metrics
2. Identify the root cause
3. Take corrective action
4. Verify the fix

Be methodical. Don't repeat the same failing command."""


def get_model_message(
    client: OpenAI,
    step: int,
    observation: str,
    last_reward: float,
    history: List[str],
    task_description: str,
) -> Dict[str, Any]:
    """Ask the LLM for the next action."""
    
    # Build conversation context
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"INCIDENT: {task_description}\n\nCurrent observation:\n{observation}\n\nLast reward: {last_reward}\nStep: {step}/{MAX_STEPS}\n\nPrevious actions:\n" + "\n".join(history[-5:]) + "\n\nWhat command should I execute next? Respond with JSON only."},
    ]
    
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.3,
            max_tokens=200,
        )
        
        content = response.choices[0].message.content.strip()
        
        # Parse JSON from response (handle markdown code blocks)
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        
        action = json.loads(content)
        return action
        
    except (json.JSONDecodeError, Exception) as e:
        # Fallback: try to extract action from text
        print(f"[DEBUG] LLM parse error: {e}", flush=True)
        return {"command": "wait", "target": "", "args": {}}


# ============================================================================
# ENVIRONMENT INTERACTION (HTTP-based for simplicity)
# ============================================================================

import urllib.request
import urllib.error


class CloudDevOpsHTTPClient:
    """Simple HTTP client for the environment when not using full OpenEnv client."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
    
    def reset(self, task: str = "identify_service_failure") -> Dict[str, Any]:
        """Reset the environment."""
        data = json.dumps({"task": task}).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/reset",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            print(f"[DEBUG] Reset error: {e}", flush=True)
            return {"observation": {}, "done": False, "reward": 0.0}
    
    def step(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Take a step in the environment."""
        data = json.dumps(action).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/step",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            print(f"[DEBUG] Step error: {e}", flush=True)
            return {"observation": {"terminal_output": f"Error: {e}", "message": str(e)}, "done": True, "reward": 0.0}
    
    def close(self):
        """No-op for HTTP client."""
        pass


def run_task_local(task_config: Dict[str, Any], client_llm: OpenAI) -> Dict[str, Any]:
    """Run a single task using local environment (no Docker/HTTP needed)."""
    # Import environment directly for local execution
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "cloud_devops_env"))
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "cloud_devops_env", "server"))
    
    from cloud_devops_env.server.environment import CloudDevOpsEnvironment
    from cloud_devops_env.models import CloudAction, CommandType
    
    task_name = task_config["name"]
    max_steps = task_config["max_steps"]
    
    env = CloudDevOpsEnvironment()
    history: List[str] = []
    rewards: List[float] = []
    trajectory: List[Dict[str, Any]] = []
    steps_taken = 0
    score = 0.0
    success = False
    
    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)
    
    try:
        # Reset environment
        result = env.reset(task=task_name)
        last_observation = result.terminal_output
        last_reward = 0.0
        task_description = result.message
        
        for step in range(1, max_steps + 1):
            if result.done:
                break
            
            # Get action from LLM
            action_dict = get_model_message(
                client_llm, step, last_observation, last_reward, history, task_description
            )
            
            # Parse and execute action
            try:
                cmd = action_dict.get("command", "wait")
                target = action_dict.get("target", "")
                args = action_dict.get("args", {})
                
                # Validate command type
                try:
                    command_type = CommandType(cmd)
                except ValueError:
                    command_type = CommandType.WAIT
                
                action = CloudAction(command=command_type, target=target, args=args)
                result = env.step(action)
                
                reward = result.reward if result.reward is not None else 0.0
                done = result.done
                error = None
                
            except Exception as e:
                reward = 0.0
                done = False
                error = str(e)
                print(f"[DEBUG] Step execution error: {e}", flush=True)
            
            rewards.append(reward)
            steps_taken = step
            last_observation = result.terminal_output if hasattr(result, 'terminal_output') else ""
            last_reward = reward
            
            action_str = json.dumps(action_dict)
            log_step(step=step, action=action_str, reward=reward, done=done, error=error)
            
            history.append(f"Step {step}: {action_str} -> reward {reward:+.2f}")
            
            # Record trajectory for grader
            trajectory.append({
                "action": action_dict,
                "observation": {
                    "terminal_output": result.terminal_output if hasattr(result, 'terminal_output') else "",
                    "message": result.message if hasattr(result, 'message') else "",
                },
                "reward": reward,
                "done": done,
            })
            
            if done:
                break
        
        # Calculate final score
        max_total_reward = 1.0  # All tasks have max reward of 1.0
        score = sum(rewards) / max_total_reward if max_total_reward > 0 else 0.0
        score = min(max(score, 0.0), 1.0)  # clamp to [0, 1]
        success = score >= SUCCESS_SCORE_THRESHOLD
        
    except Exception as e:
        print(f"[DEBUG] Task error: {e}", flush=True)
    
    log_end(success=success, steps=steps_taken, score=score, rewards=rewards)
    
    return {
        "task": task_name,
        "score": score,
        "steps": steps_taken,
        "success": success,
        "rewards": rewards,
        "trajectory": trajectory,
    }


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main() -> None:
    """Run all 3 tasks and produce baseline scores."""
    client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)
    
    print(f"[INFO] CloudDevOps-Env Baseline Inference", flush=True)
    print(f"[INFO] Model: {MODEL_NAME}", flush=True)
    print(f"[INFO] Tasks: {len(TASKS)}", flush=True)
    print(f"[INFO] {'='*50}", flush=True)
    
    all_results = []
    
    for task_config in TASKS:
        print(f"\n[INFO] Running task: {task_config['name']} ({task_config['difficulty']})", flush=True)
        result = run_task_local(task_config, client)
        all_results.append(result)
        print(f"[INFO] Task {task_config['name']}: score={result['score']:.2f}, steps={result['steps']}, success={result['success']}", flush=True)
    
    # Summary
    print(f"\n[INFO] {'='*50}", flush=True)
    print(f"[INFO] BASELINE RESULTS SUMMARY", flush=True)
    print(f"[INFO] {'='*50}", flush=True)
    
    total_score = 0.0
    for result in all_results:
        total_score += result["score"]
        status = "PASS" if result["success"] else "FAIL"
        print(f"[INFO]   {result['task']}: {result['score']:.2f} [{status}]", flush=True)
    
    avg_score = total_score / len(all_results)
    print(f"[INFO]   Average score: {avg_score:.2f}", flush=True)


if __name__ == "__main__":
    main()
