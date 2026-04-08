"""
CloudDevOps-Env: Incident Scenarios
Defines three realistic SRE incident scenarios with increasing difficulty.
Each scenario contains the simulated infrastructure state, expected solutions,
and reward checkpoints.
"""

import copy
from typing import Dict, List, Any

# ============================================================================
# TASK 1: IDENTIFY SERVICE FAILURE (Easy)
# ============================================================================
TASK_1_IDENTIFY_FAILURE = {
    "name": "identify_service_failure",
    "difficulty": "easy",
    "description": "A web service is returning HTTP 500 errors. Find the failing service, diagnose the root cause, and restart it.",
    "max_steps": 10,
    "initial_alerts": [
        "CRITICAL: HTTP 500 error rate spike on api-gateway (>50% of requests failing)",
        "WARNING: Upstream connection failures from api-gateway to backend services",
        "INFO: Load balancer health checks failing for 2/5 backend instances",
    ],
    "services": {
        "api-gateway": {"status": "degraded", "cpu": "15%", "memory": "220MB", "uptime": "45d", "health": "unhealthy"},
        "auth-service": {"status": "running", "cpu": "8%", "memory": "180MB", "uptime": "45d", "health": "healthy"},
        "user-service": {"status": "crashed", "cpu": "0%", "memory": "0MB", "uptime": "0s", "health": "dead"},
        "payment-service": {"status": "running", "cpu": "12%", "memory": "340MB", "uptime": "45d", "health": "healthy"},
        "notification-service": {"status": "running", "cpu": "5%", "memory": "120MB", "uptime": "45d", "health": "healthy"},
    },
    "logs": {
        "api-gateway": [
            "[ERROR] 2026-04-08T10:00:01Z upstream connect error: connection refused to user-service:8080",
            "[ERROR] 2026-04-08T10:00:02Z upstream connect error: connection refused to user-service:8080",
            "[WARN]  2026-04-08T09:59:58Z circuit breaker opened for user-service after 10 consecutive failures",
            "[INFO]  2026-04-08T09:59:50Z health check failed for user-service: connection refused",
            "[ERROR] 2026-04-08T10:00:03Z returning 502 Bad Gateway for GET /api/v1/users/profile",
        ],
        "user-service": [
            "[FATAL] 2026-04-08T09:59:45Z OutOfMemoryError: Java heap space",
            "[ERROR] 2026-04-08T09:59:44Z GC overhead limit exceeded - 98% of time spent in GC",
            "[WARN]  2026-04-08T09:59:40Z Memory usage critical: 1950MB / 2048MB heap",
            "[INFO]  2026-04-08T09:59:30Z Processing batch user sync job (50000 records)",
            "[INFO]  2026-04-08T09:58:00Z Service started successfully on port 8080",
        ],
        "auth-service": [
            "[INFO]  2026-04-08T10:00:01Z Processed 150 auth requests in last minute",
            "[INFO]  2026-04-08T09:55:00Z Token cache refreshed successfully",
        ],
        "payment-service": [
            "[INFO]  2026-04-08T10:00:00Z Processed 45 transactions in last minute",
            "[WARN]  2026-04-08T09:58:00Z Slow query detected: get_user_payment_methods (user-service dependency timeout)",
        ],
        "notification-service": [
            "[INFO]  2026-04-08T10:00:00Z Queue depth: 23 messages pending",
            "[WARN]  2026-04-08T09:59:50Z Failed to fetch user preferences from user-service",
        ],
    },
    "diagnostics": {
        "api-gateway": "Reverse proxy forwarding requests. user-service backend marked DOWN. 502 errors being returned for /api/v1/users/* endpoints.",
        "user-service": "Process exited with code 137 (OOM killed). Last known state: Java heap exhausted during batch sync job. Recommendation: restart with increased heap or disable batch job.",
        "auth-service": "All systems nominal. JWT validation pipeline healthy.",
        "payment-service": "Operational but experiencing timeouts on user-service dependent queries.",
        "notification-service": "Operational. Some user preference lookups failing due to user-service outage.",
    },
    "metrics": {
        "api-gateway": {"requests_per_sec": 850, "error_rate": "52%", "p99_latency_ms": 12000, "active_connections": 342},
        "user-service": {"requests_per_sec": 0, "error_rate": "100%", "p99_latency_ms": 0, "active_connections": 0},
        "auth-service": {"requests_per_sec": 150, "error_rate": "0.1%", "p99_latency_ms": 45, "active_connections": 28},
        "payment-service": {"requests_per_sec": 45, "error_rate": "8%", "p99_latency_ms": 3500, "active_connections": 12},
        "notification-service": {"requests_per_sec": 30, "error_rate": "5%", "p99_latency_ms": 200, "active_connections": 8},
    },
    # Solution state tracking
    "solution": {
        "target_service": "user-service",
        "root_cause": "OOM",
        "required_action": "restart_service",
        "checkpoints": {
            "identified_failing_service": False,  # 0.3 points
            "diagnosed_root_cause": False,         # 0.4 points
            "restarted_service": False,            # 0.3 points
        },
    },
}


# ============================================================================
# TASK 2: DIAGNOSE MEMORY LEAK (Medium)
# ============================================================================
TASK_2_MEMORY_LEAK = {
    "name": "diagnose_memory_leak",
    "difficulty": "medium",
    "description": "A microservice is experiencing a gradual memory leak causing periodic OOM kills. Find the leak source, identify the problematic component, and apply the fix.",
    "max_steps": 15,
    "initial_alerts": [
        "WARNING: payment-service memory usage at 85% and climbing steadily",
        "INFO: payment-service has been OOM-killed 3 times in the last 24 hours",
        "WARNING: payment-service response times degrading (p99 > 2000ms)",
        "INFO: Auto-restart policy triggered for payment-service",
    ],
    "services": {
        "api-gateway": {"status": "running", "cpu": "18%", "memory": "250MB", "uptime": "30d", "health": "healthy"},
        "auth-service": {"status": "running", "cpu": "10%", "memory": "200MB", "uptime": "30d", "health": "healthy"},
        "user-service": {"status": "running", "cpu": "15%", "memory": "350MB", "uptime": "30d", "health": "healthy"},
        "payment-service": {"status": "running", "cpu": "45%", "memory": "1800MB", "uptime": "2h", "health": "degraded"},
        "cache-service": {"status": "running", "cpu": "22%", "memory": "512MB", "uptime": "30d", "health": "healthy"},
        "notification-service": {"status": "running", "cpu": "5%", "memory": "120MB", "uptime": "30d", "health": "healthy"},
    },
    "logs": {
        "payment-service": [
            "[WARN]  2026-04-08T09:50:00Z Memory usage: 1800MB / 2048MB (87.8%)",
            "[WARN]  2026-04-08T09:45:00Z Memory usage: 1650MB / 2048MB (80.5%)",
            "[WARN]  2026-04-08T09:40:00Z Memory usage: 1500MB / 2048MB (73.2%)",
            "[INFO]  2026-04-08T09:35:00Z GC cycle completed: freed 50MB, heap still at 1350MB",
            "[WARN]  2026-04-08T09:30:00Z Connection pool 'redis-sessions': 450 active connections (max: 500)",
            "[DEBUG] 2026-04-08T09:25:00Z Session cache size: 125000 entries (expected: ~5000 for current load)",
            "[WARN]  2026-04-08T09:20:00Z Redis session cleanup job: 0 expired sessions cleaned (TTL not set on 120000 entries)",
            "[ERROR] 2026-04-08T07:30:00Z OOM killed (exit code 137). Auto-restarting...",
            "[ERROR] 2026-04-08T03:15:00Z OOM killed (exit code 137). Auto-restarting...",
            "[ERROR] 2026-04-07T22:00:00Z OOM killed (exit code 137). Auto-restarting...",
            "[INFO]  2026-04-07T14:00:00Z Deployed version 2.4.1 - Added session caching layer",
        ],
        "cache-service": [
            "[INFO]  2026-04-08T09:50:00Z Redis memory usage: 480MB / 1024MB",
            "[WARN]  2026-04-08T09:45:00Z Client payment-service: 450 connections (unusually high)",
            "[INFO]  2026-04-08T09:40:00Z Eviction policy: noeviction (WARN: no auto-cleanup)",
            "[INFO]  2026-04-08T09:35:00Z Keys with no TTL: 120,432 (namespace: payment-sessions:*)",
        ],
        "api-gateway": [
            "[WARN]  2026-04-08T09:50:00Z payment-service latency spike: p99 = 2100ms",
            "[INFO]  2026-04-08T09:45:00Z All backends healthy",
        ],
        "auth-service": ["[INFO]  2026-04-08T09:50:00Z Normal operation"],
        "user-service": ["[INFO]  2026-04-08T09:50:00Z Normal operation"],
        "notification-service": ["[INFO]  2026-04-08T09:50:00Z Normal operation"],
    },
    "diagnostics": {
        "payment-service": "Memory growing linearly at ~150MB/hour since version 2.4.1 deployment. Session cache not expiring entries. Redis connection pool near capacity (450/500). Root cause: session objects stored without TTL in local cache AND Redis, causing unbounded growth.",
        "cache-service": "Redis healthy but storing 120K+ keys with no TTL in payment-sessions:* namespace. Memory stable but keys growing. Needs TTL policy applied.",
        "api-gateway": "Healthy. Forwarding traffic normally. Payment-service latency elevated.",
        "auth-service": "All systems nominal.",
        "user-service": "All systems nominal.",
        "notification-service": "All systems nominal.",
    },
    "metrics": {
        "payment-service": {"requests_per_sec": 120, "error_rate": "2%", "p99_latency_ms": 2100, "memory_growth_mb_per_hour": 150, "active_connections": 450, "session_cache_entries": 125000},
        "cache-service": {"requests_per_sec": 500, "error_rate": "0%", "p99_latency_ms": 5, "memory_mb": 480, "total_keys": 185000, "keys_without_ttl": 120432},
        "api-gateway": {"requests_per_sec": 900, "error_rate": "1%", "p99_latency_ms": 2200, "active_connections": 380},
        "auth-service": {"requests_per_sec": 150, "error_rate": "0%", "p99_latency_ms": 40, "active_connections": 25},
        "user-service": {"requests_per_sec": 200, "error_rate": "0%", "p99_latency_ms": 80, "active_connections": 40},
        "notification-service": {"requests_per_sec": 30, "error_rate": "0%", "p99_latency_ms": 150, "active_connections": 8},
    },
    "solution": {
        "target_service": "payment-service",
        "root_cause": "session_cache_no_ttl",
        "leak_component": "session-cache",
        "required_actions": ["kill_process", "apply_fix"],
        "checkpoints": {
            "identified_leaking_service": False,   # 0.2 points
            "found_leak_source": False,            # 0.3 points
            "applied_fix": False,                  # 0.2 points
            "verified_fix": False,                 # 0.3 points
        },
    },
}


# ============================================================================
# TASK 3: DATABASE ROLLBACK UNDER PRESSURE (Hard)
# ============================================================================
TASK_3_DB_ROLLBACK = {
    "name": "database_rollback",
    "difficulty": "hard",
    "description": "A bad database migration has corrupted critical data. Find the problematic migration, safely stop dependent services, execute a rollback, and verify data integrity — all while the system continues to degrade.",
    "max_steps": 20,
    "initial_alerts": [
        "CRITICAL: Data integrity errors detected in orders table - NULL values in required fields",
        "CRITICAL: payment-service throwing DataIntegrityViolation errors (500+ in last 5 min)",
        "WARNING: order-service returning corrupted order data to customers",
        "WARNING: Database migration 'v2.8.0_add_payment_fields' completed 30 minutes ago",
        "INFO: Revenue impact estimated at $15,000/minute due to failed checkouts",
        "ESCALATION: On-call SRE paged - P1 incident declared",
    ],
    "services": {
        "api-gateway": {"status": "running", "cpu": "35%", "memory": "300MB", "uptime": "60d", "health": "degraded"},
        "auth-service": {"status": "running", "cpu": "10%", "memory": "200MB", "uptime": "60d", "health": "healthy"},
        "user-service": {"status": "running", "cpu": "20%", "memory": "400MB", "uptime": "60d", "health": "healthy"},
        "order-service": {"status": "running", "cpu": "55%", "memory": "600MB", "uptime": "60d", "health": "critical"},
        "payment-service": {"status": "running", "cpu": "60%", "memory": "500MB", "uptime": "60d", "health": "critical"},
        "inventory-service": {"status": "running", "cpu": "15%", "memory": "250MB", "uptime": "60d", "health": "healthy"},
        "notification-service": {"status": "running", "cpu": "25%", "memory": "180MB", "uptime": "60d", "health": "degraded"},
        "database": {"status": "running", "cpu": "78%", "memory": "3200MB", "uptime": "60d", "health": "degraded", "connections": "180/200"},
    },
    "logs": {
        "database": [
            "[INFO]  2026-04-08T09:30:00Z Migration v2.8.0_add_payment_fields COMPLETED",
            "[INFO]  2026-04-08T09:30:00Z ALTER TABLE orders ADD COLUMN payment_method_id INTEGER",
            "[INFO]  2026-04-08T09:30:01Z ALTER TABLE orders ADD COLUMN payment_processor VARCHAR(50)",
            "[ERROR] 2026-04-08T09:30:02Z UPDATE orders SET payment_method_id = NULL WHERE payment_method_id IS NULL -- affected 450,000 rows",
            "[WARN]  2026-04-08T09:30:02Z Column payment_method_id added as NULLABLE but application expects NOT NULL",
            "[INFO]  2026-04-08T09:29:50Z Migration v2.7.9_fix_user_index COMPLETED - OK",
            "[INFO]  2026-04-08T09:29:45Z Migration v2.7.8_add_audit_log COMPLETED - OK",
            "[ERROR] 2026-04-08T09:35:00Z Constraint violation: orders.payment_method_id cannot be null for active orders",
            "[ERROR] 2026-04-08T09:40:00Z 500+ constraint violations in last 5 minutes",
            "[WARN]  2026-04-08T09:45:00Z Connection pool nearing limit: 180/200 active connections",
            "[WARN]  2026-04-08T09:50:00Z Deadlock detected on table 'orders' - retrying transactions",
        ],
        "order-service": [
            "[ERROR] 2026-04-08T09:35:01Z DataIntegrityViolationException: Column 'payment_method_id' cannot be null",
            "[ERROR] 2026-04-08T09:35:02Z Failed to process order #ORD-2026-584301: payment_method_id is null",
            "[ERROR] 2026-04-08T09:35:03Z Order fetch returning corrupted data for orders created before migration",
            "[WARN]  2026-04-08T09:40:00Z 234 orders in ERROR state in last 10 minutes",
            "[WARN]  2026-04-08T09:45:00Z Customer complaints increasing - support queue at 150 tickets",
            "[ERROR] 2026-04-08T09:50:00Z Retry storm: 5000+ failed retries consuming thread pool",
        ],
        "payment-service": [
            "[ERROR] 2026-04-08T09:35:00Z NullPointerException at PaymentProcessor.process(): order.paymentMethodId is null",
            "[ERROR] 2026-04-08T09:35:01Z Payment processing failed for 89% of requests",
            "[WARN]  2026-04-08T09:40:00Z Thread pool exhausted - 200/200 threads blocked on DB queries",
            "[ERROR] 2026-04-08T09:45:00Z Circuit breaker OPEN for order-service dependency",
            "[CRITICAL] 2026-04-08T09:50:00Z Revenue loss estimated: $450,000 in last 20 minutes",
        ],
        "api-gateway": [
            "[WARN]  2026-04-08T09:35:00Z Error rate spike: /api/v1/orders/* returning 500 (45% of requests)",
            "[WARN]  2026-04-08T09:40:00Z Error rate: /api/v1/payments/* returning 500 (89% of requests)",
            "[INFO]  2026-04-08T09:45:00Z Rate limiting applied to prevent cascade failure",
        ],
        "auth-service": ["[INFO]  2026-04-08T09:50:00Z Normal operation"],
        "user-service": ["[INFO]  2026-04-08T09:50:00Z Normal operation"],
        "inventory-service": [
            "[WARN]  2026-04-08T09:40:00Z Inventory reservation failures: order-service returning errors",
            "[INFO]  2026-04-08T09:45:00Z Compensating: releasing 156 held inventory reservations",
        ],
        "notification-service": [
            "[ERROR] 2026-04-08T09:40:00Z Failed to send order confirmation: order data corrupted",
            "[WARN]  2026-04-08T09:45:00Z Notification queue backing up: 2300 pending messages",
        ],
    },
    "diagnostics": {
        "database": "Migration v2.8.0_add_payment_fields added nullable columns to orders table. Application code expects NOT NULL. 450,000 historical orders now have NULL payment_method_id. Rollback available: v2.8.0_add_payment_fields_rollback. WARNING: Must stop order-service and payment-service before rollback to prevent data corruption during migration reversal.",
        "order-service": "DataIntegrityViolation errors from NULL payment_method_id. Retry storm consuming 100% thread pool. Needs immediate shutdown before DB rollback.",
        "payment-service": "NullPointerExceptions from order data. Circuit breaker open. Revenue impact critical. Needs shutdown before DB rollback.",
        "api-gateway": "Error rates elevated on order and payment endpoints. Otherwise functional.",
        "auth-service": "All systems nominal.",
        "user-service": "All systems nominal.",
        "inventory-service": "Some reservation failures but self-healing. Not directly affected by migration.",
        "notification-service": "Queue backing up due to order failures. Will self-resolve after fix.",
    },
    "metrics": {
        "database": {"queries_per_sec": 2500, "error_rate": "15%", "deadlocks_per_min": 12, "connections": "180/200", "replication_lag_ms": 500},
        "order-service": {"requests_per_sec": 300, "error_rate": "78%", "p99_latency_ms": 15000, "active_connections": 200, "orders_in_error": 1234},
        "payment-service": {"requests_per_sec": 200, "error_rate": "89%", "p99_latency_ms": 30000, "active_connections": 200, "revenue_loss_per_min": 15000},
        "api-gateway": {"requests_per_sec": 1200, "error_rate": "35%", "p99_latency_ms": 20000, "active_connections": 500},
        "auth-service": {"requests_per_sec": 150, "error_rate": "0%", "p99_latency_ms": 40, "active_connections": 25},
        "user-service": {"requests_per_sec": 200, "error_rate": "0%", "p99_latency_ms": 80, "active_connections": 40},
        "inventory-service": {"requests_per_sec": 100, "error_rate": "12%", "p99_latency_ms": 500, "active_connections": 30},
        "notification-service": {"requests_per_sec": 30, "error_rate": "25%", "p99_latency_ms": 1000, "active_connections": 15},
    },
    "migrations": [
        {"id": "v2.7.8_add_audit_log", "status": "applied", "safe": True, "timestamp": "2026-04-08T09:29:45Z"},
        {"id": "v2.7.9_fix_user_index", "status": "applied", "safe": True, "timestamp": "2026-04-08T09:29:50Z"},
        {"id": "v2.8.0_add_payment_fields", "status": "applied", "safe": False, "timestamp": "2026-04-08T09:30:00Z",
         "rollback_sql": "ALTER TABLE orders DROP COLUMN payment_method_id; ALTER TABLE orders DROP COLUMN payment_processor;"},
    ],
    "solution": {
        "bad_migration": "v2.8.0_add_payment_fields",
        "services_to_stop": ["order-service", "payment-service"],
        "required_actions": ["stop_service", "stop_service", "rollback_migration", "start_service", "start_service", "verify_health"],
        "checkpoints": {
            "found_bad_migration": False,         # 0.15 points
            "stopped_dependent_services": False,   # 0.15 points
            "executed_rollback": False,            # 0.30 points
            "restarted_services": False,           # 0.20 points
            "verified_health": False,              # 0.20 points
        },
    },
}


def get_scenario(task_name: str) -> Dict[str, Any]:
    """Get a deep copy of a scenario by task name."""
    scenarios = {
        "identify_service_failure": TASK_1_IDENTIFY_FAILURE,
        "diagnose_memory_leak": TASK_2_MEMORY_LEAK,
        "database_rollback": TASK_3_DB_ROLLBACK,
    }
    if task_name not in scenarios:
        raise ValueError(f"Unknown task: {task_name}. Available: {list(scenarios.keys())}")
    return copy.deepcopy(scenarios[task_name])


def get_all_task_names() -> List[str]:
    """Return all available task names."""
    return ["identify_service_failure", "diagnose_memory_leak", "database_rollback"]
