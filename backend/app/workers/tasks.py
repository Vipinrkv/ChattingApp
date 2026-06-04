import asyncio

from app.core.task_queue import task_queue


def run_distributed_task(task_name: str, *args, **kwargs):
    """RQ-compatible bridge for distributed tasks registered at runtime."""
    task = task_queue.distributed_task_registry.get(task_name)
    if not task:
        raise RuntimeError(f"Distributed task {task_name} is not registered")
    result = task(*args, **kwargs)
    if asyncio.iscoroutine(result):
        return asyncio.run(result)
    return result
