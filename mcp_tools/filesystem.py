"""FileSystem MCP - Safe workspace file operations."""

from pathlib import Path
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class FileSystemMCP:
    """Safe file system operations restricted to workspace."""
    
    def __init__(self, workspace_root: str = "/workspace"):
        self.workspace_root = Path(workspace_root).resolve()
        logger.info(f"FileSystem MCP initialized with workspace: {self.workspace_root}")
    
    def _validate_path(self, path: str) -> Path:
        """Validate that path is within workspace (security check)."""
        resolved_path = (self.workspace_root / path).resolve()
        
        # Prevent path traversal attacks
        if not str(resolved_path).startswith(str(self.workspace_root)):
            raise ValueError(f"Path {path} is outside workspace")
        
        return resolved_path
    
    def read_file(self, path: str) -> str:
        """Read file contents.
        
        Args:
            path: Relative path within workspace
        
        Returns:
            File contents as string
        """
        try:
            file_path = self._validate_path(path)
            
            if not file_path.exists():
                raise FileNotFoundError(f"File {path} does not exist")
            
            if not file_path.is_file():
                raise ValueError(f"Path {path} is not a file")
            
            content = file_path.read_text()
            logger.info(f"Read file: {path}")
            return content
        
        except Exception as e:
            logger.error(f"Failed to read file {path}: {e}")
            raise
    
    def write_file(self, path: str, content: str):
        """Write content to file (creates parent directories if needed).
        
        Args:
            path: Relative path within workspace
            content: File content to write
        """
        try:
            file_path = self._validate_path(path)
            
            # Create parent directories if they don't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_path.write_text(content)
            logger.info(f"Wrote file: {path}")
        
        except Exception as e:
            logger.error(f"Failed to write file {path}: {e}")
            raise
    
    def list_dir(self, path: str = ".", recursive: bool = False) -> List[Dict]:
        """List directory contents.
        
        Args:
            path: Relative path within workspace (default: root)
            recursive: If True, list recursively
        
        Returns:
            List of file/directory information
        """
        try:
            dir_path = self._validate_path(path)
            
            if not dir_path.exists():
                raise FileNotFoundError(f"Directory {path} does not exist")
            
            if not dir_path.is_dir():
                raise ValueError(f"Path {path} is not a directory")
            
            results = []
            
            if recursive:
                pattern = "**/*"
            else:
                pattern = "*"
            
            for item in dir_path.glob(pattern):
                relative_path = item.relative_to(self.workspace_root)
                
                results.append({
                    "path": str(relative_path),
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else None
                })
            
            logger.info(f"Listed directory {path}: {len(results)} items")
            return results
        
        except Exception as e:
            logger.error(f"Failed to list directory {path}: {e}")
            raise
    
    def delete_file(self, path: str):
        """Delete a file.
        
        Args:
            path: Relative path within workspace
        """
        try:
            file_path = self._validate_path(path)
            
            if not file_path.exists():
                raise FileNotFoundError(f"File {path} does not exist")
            
            if file_path.is_dir():
                raise ValueError(f"Path {path} is a directory, use rmdir instead")
            
            file_path.unlink()
            logger.info(f"Deleted file: {path}")
        
        except Exception as e:
            logger.error(f"Failed to delete file {path}: {e}")
            raise
