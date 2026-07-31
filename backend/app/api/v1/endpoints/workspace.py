from fastapi import APIRouter, Query, HTTPException, status, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from app.workspace.manager import WorkspaceManager
from app.core.config import settings
from app.core.auth import get_current_user
from app.db.models import User
from app.tools.exceptions import PathTraversalError, ToolFileNotFoundError, ToolExecutionError

router = APIRouter()

def get_workspace_manager(current_user: User = Depends(get_current_user)) -> WorkspaceManager:
    user_dir = settings.WORKSPACE_DIR / "users" / str(current_user.id)
    user_dir.mkdir(parents=True, exist_ok=True)
    return WorkspaceManager(workspace_root=user_dir)

# Schemas for Endpoint Bodies
class FileCreateBody(BaseModel):
    path: str = Field(..., description="Path to create file, relative to workspace root")
    content: str = Field(..., description="Content of the file")
    overwrite: bool = Field(False, description="Whether to overwrite if file already exists")

class FileUpdateBody(BaseModel):
    path: str = Field(..., description="Path of the file to update, relative to workspace root")
    content: str = Field(..., description="New/replacement content")
    target_content: Optional[str] = Field(None, description="Optional block of content to replace (partial edit)")
    confirm: bool = Field(True, description="Whether to apply changes directly or just return diff for review")

class ProjectCreateBody(BaseModel):
    project_type: str = Field(..., description="Project type: fastapi, flask, cli, package, script")
    name: str = Field(..., description="Name of the project folder")

# Response models
class FilesListResponse(BaseModel):
    files: List[str]
    tracking: Dict[str, List[str]]

class FileReadResponse(BaseModel):
    path: str
    content: str

class FileWriteResponse(BaseModel):
    path: str
    success: bool
    message: str

class FileUpdateResponse(BaseModel):
    path: str
    applied: bool
    message: str
    diff: Optional[str] = None

class ProjectCreateResponse(BaseModel):
    message: str


@router.get("/files", response_model=FilesListResponse)
def list_files(
    path: str = ".",
    manager: WorkspaceManager = Depends(get_workspace_manager)
):
    """Lists files recursively from a directory in the workspace, along with tracking status."""
    try:
        files = manager.list_files(path)
        tracking = manager.get_tracking_status()
        return FilesListResponse(files=files, tracking=tracking)
    except PathTraversalError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ToolFileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ToolExecutionError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/file", response_model=FileReadResponse)
def read_file(
    path: str = Query(..., description="File path relative to workspace root"),
    manager: WorkspaceManager = Depends(get_workspace_manager)
):
    """Reads the content of a file in the workspace."""
    try:
        content = manager.read_file(path)
        return FileReadResponse(path=path, content=content)
    except PathTraversalError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ToolFileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ToolExecutionError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/file", response_model=FileWriteResponse)
def create_file(
    body: FileCreateBody,
    manager: WorkspaceManager = Depends(get_workspace_manager)
):
    """Creates a new file in the workspace."""
    try:
        msg = manager.create_file(body.path, body.content, overwrite=body.overwrite)
        return FileWriteResponse(path=body.path, success=True, message=msg)
    except PathTraversalError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ToolExecutionError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/file", response_model=FileUpdateResponse)
def update_file(
    body: FileUpdateBody,
    manager: WorkspaceManager = Depends(get_workspace_manager)
):
    """Updates a file in the workspace. Supports partial edits and diff confirmations."""
    try:
        applied, msg, diff = manager.update_file(
            body.path, body.content, confirm=body.confirm, target_content=body.target_content
        )
        return FileUpdateResponse(path=body.path, applied=applied, message=msg, diff=diff)
    except PathTraversalError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ToolFileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ToolExecutionError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/file")
def delete_file(
    path: str = Query(..., description="File or directory path relative to workspace root"),
    manager: WorkspaceManager = Depends(get_workspace_manager)
):
    """Deletes a file or directory in the workspace."""
    try:
        msg = manager.delete_file(path)
        return {"success": True, "message": msg}
    except PathTraversalError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ToolFileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ToolExecutionError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/project", response_model=ProjectCreateResponse)
def create_project(
    body: ProjectCreateBody,
    manager: WorkspaceManager = Depends(get_workspace_manager)
):
    """Generates a boilerplate project template (fastapi, flask, cli, package, script) inside the workspace."""
    try:
        msg = manager.create_project(body.project_type, body.name)
        return ProjectCreateResponse(message=msg)
    except PathTraversalError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ToolExecutionError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
