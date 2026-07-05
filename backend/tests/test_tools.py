import os
import pytest
from pathlib import Path
from app.core.config import settings
from app.tools.fs_tools import (
    resolve_workspace_path,
    write_file,
    read_file,
    list_directory
)

def test_resolve_workspace_path():
    valid_path = "subdir/test_file.txt"
    resolved = resolve_workspace_path(valid_path)
    expected = (settings.WORKSPACE_DIR / valid_path).resolve(strict=False)
    assert resolved == expected

    invalid_path = "../../../outside.txt"
    with pytest.raises(ValueError) as excinfo:
        resolve_workspace_path(invalid_path)
    assert "Security Violation" in str(excinfo.value)

def test_write_and_read_file(tmp_path):
    original_workspace = settings.WORKSPACE_DIR
    settings.WORKSPACE_DIR = tmp_path
    
    try:
        file_path = "sub/hello.txt"
        content = "Hello, CodeForge AI!"
        
        write_res = write_file(file_path, content)
        assert "successfully written" in write_res
        
        physical_file = tmp_path / file_path
        assert physical_file.exists()
        assert physical_file.read_text(encoding="utf-8") == content

        read_res = read_file(file_path)
        assert read_res == content

        missing_res = read_file("does_not_exist.txt")
        assert "Error: File" in missing_res and "does not exist" in missing_res
        
    finally:
        settings.WORKSPACE_DIR = original_workspace

def test_list_directory(tmp_path):
    original_workspace = settings.WORKSPACE_DIR
    settings.WORKSPACE_DIR = tmp_path
    
    try:
        (tmp_path / "file1.txt").write_text("file 1")
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "file2.txt").write_text("file 2")

        res = list_directory(".")
        assert "file1.txt" in res
        assert "sub" in res
        
        sub_res = list_directory("sub")
        assert "sub/file2.txt" in sub_res
        
    finally:
        settings.WORKSPACE_DIR = original_workspace
