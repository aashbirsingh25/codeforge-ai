from fastapi import APIRouter

router = APIRouter()

@router.get("")
def list_agents():
    """
    Get configured autonomous software engineering sub-agents.
    """
    return {
        "agents": [
            {
                "id": "planner",
                "name": "Planner Agent",
                "role": "Planning and task deconstruction",
                "status": "ready"
            },
            {
                "id": "coding",
                "name": "Coding Agent",
                "role": "Code generation and modifications",
                "status": "ready"
            },
            {
                "id": "reviewer",
                "name": "Reviewer Agent",
                "role": "Code review and style verification",
                "status": "ready"
            },
            {
                "id": "debugger",
                "name": "Debugger Agent",
                "role": "Error analysis and correction loops",
                "status": "ready"
            }
        ]
    }
