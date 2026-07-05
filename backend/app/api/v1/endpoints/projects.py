from fastapi import APIRouter

router = APIRouter()

@router.get("")
def list_projects():
    """
    Get a list of active repositories / projects managed by CodeForge.
    """
    return {
        "projects": [
            {
                "id": "proj_placeholder_1",
                "name": "CodeForge Workspace",
                "path": "./workspace",
                "status": "active"
            }
        ]
    }
