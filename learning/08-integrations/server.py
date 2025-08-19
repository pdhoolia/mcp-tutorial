# Complete task management MCP server
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from mcp.server.fastmcp import FastMCP
import json
import sys

# Create server with HTTP support
mcp = FastMCP(
    "Task Manager",
    host="localhost",
    port=8000
)

# Task model
class Task(BaseModel):
    id: str
    title: str
    description: str = ""
    status: str = "pending"  # pending, in_progress, completed
    priority: int = Field(default=3, ge=1, le=5)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    tags: List[str] = []

# In-memory task storage (use database in production)
tasks_db: dict[str, Task] = {}
next_id = 1

@mcp.tool()
def create_task(
    title: str, 
    description: str = "", 
    priority: int = 3,
    tags: List[str] = []
) -> Task:
    """Create a new task"""
    global next_id
    task_id = f"task_{next_id}"
    next_id += 1
    
    task = Task(
        id=task_id,
        title=title,
        description=description,
        priority=priority,
        tags=tags
    )
    tasks_db[task_id] = task
    return task

@mcp.tool()
def update_task_status(task_id: str, status: str) -> Task:
    """Update task status"""
    if task_id not in tasks_db:
        raise ValueError(f"Task {task_id} not found")
    
    if status not in ["pending", "in_progress", "completed"]:
        raise ValueError(f"Invalid status: {status}")
    
    task = tasks_db[task_id]
    task.status = status
    task.updated_at = datetime.now()
    return task

@mcp.tool()
def list_tasks(
    status: Optional[str] = None,
    tag: Optional[str] = None
) -> List[Task]:
    """List tasks with optional filtering"""
    tasks = list(tasks_db.values())
    
    if status:
        tasks = [t for t in tasks if t.status == status]
    
    if tag:
        tasks = [t for t in tasks if tag in t.tags]
    
    # Sort by priority (high to low) and creation time
    tasks.sort(key=lambda t: (-t.priority, t.created_at))
    return tasks

@mcp.tool()
def get_task_stats() -> dict:
    """Get task statistics"""
    total = len(tasks_db)
    by_status = {
        "pending": sum(1 for t in tasks_db.values() if t.status == "pending"),
        "in_progress": sum(1 for t in tasks_db.values() if t.status == "in_progress"),
        "completed": sum(1 for t in tasks_db.values() if t.status == "completed")
    }
    
    avg_priority = sum(t.priority for t in tasks_db.values()) / total if total > 0 else 0
    
    return {
        "total_tasks": total,
        "by_status": by_status,
        "average_priority": round(avg_priority, 2),
        "completion_rate": round(by_status["completed"] / total * 100, 1) if total > 0 else 0
    }

@mcp.resource("tasks://all")
def export_all_tasks() -> str:
    """Export all tasks as JSON"""
    tasks_list = [task.model_dump() for task in tasks_db.values()]
    # Convert datetime objects to strings
    for task in tasks_list:
        task['created_at'] = task['created_at'].isoformat()
        task['updated_at'] = task['updated_at'].isoformat()
    return json.dumps(tasks_list, indent=2)

@mcp.resource("tasks://summary")
def get_task_summary() -> str:
    """Get a summary of current tasks"""
    stats = get_task_stats()
    summary = f"""Task Summary
=============
Total Tasks: {stats['total_tasks']}
Pending: {stats['by_status']['pending']}
In Progress: {stats['by_status']['in_progress']}
Completed: {stats['by_status']['completed']}
Completion Rate: {stats['completion_rate']}%
Average Priority: {stats['average_priority']}/5
"""
    return summary

@mcp.prompt(title="Daily Standup")
def daily_standup() -> str:
    """Generate a daily standup report"""
    in_progress = list_tasks(status="in_progress")
    completed_today = [
        t for t in list_tasks(status="completed")
        if t.updated_at.date() == datetime.now().date()
    ]
    high_priority_pending = [
        t for t in list_tasks(status="pending")
        if t.priority >= 4
    ]
    
    report = "Daily Standup Report\n\n"
    
    report += "📋 In Progress:\n"
    for task in in_progress:
        report += f"  - {task.title} (Priority: {task.priority})\n"
    
    report += "\n✅ Completed Today:\n"
    for task in completed_today:
        report += f"  - {task.title}\n"
    
    report += "\n🔥 High Priority Pending:\n"
    for task in high_priority_pending:
        report += f"  - {task.title} (Priority: {task.priority})\n"
    
    return report

if __name__ == "__main__":
    # Determine transport mode from command line argument
    # Valid options: stdio, sse, streamable-http
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    
    print(f"\nStarting Task Manager MCP Server")
    
    # Handle different transport modes
    if transport == "sse":
        print(f"\nStarting SSE server on http://localhost:8000")
        mcp.run(transport="sse")
    elif transport == "streamable-http":
        print(f"\nStarting Streamable HTTP server on http://localhost:8000")
        mcp.run(transport="streamable-http")
    else:
        print("\nStarting in stdio mode")
        mcp.run(transport="stdio")