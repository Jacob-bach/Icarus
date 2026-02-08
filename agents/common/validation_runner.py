"""Code validation runner for Builder agent.

This module runs linters and basic tests on generated code to provide
feedback for the reflection engine.
"""

import subprocess
import json
import ast
from pathlib import Path
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class ValidationRunner:
    """Runs linters and syntax checks on generated code."""
    
    def __init__(self, workspace_path: str = "/workspace"):
        """Initialize validation runner.
        
        Args:
            workspace_path: Path to workspace directory
        """
        self.workspace = Path(workspace_path)
        logger.info(f"ValidationRunner initialized with workspace: {workspace_path}")
    
    async def validate_python_code(self, file_path: str) -> Dict:
        """Run Python linters and syntax checks on code.
        
        Args:
            file_path: Relative path to file within workspace
            
        Returns:
            Dict with:
                - success (bool): True if no errors
                - errors (List[str]): List of error messages
                - warnings (List[str]): List of warning messages
        """
        full_path = self.workspace / file_path
        errors = []
        warnings = []
        
        if not full_path.exists():
            return {
                "success": False,
                "errors": [f"File not found: {file_path}"],
                "warnings": []
            }
        
        # Step 1: Check syntax
        syntax_errors = await self._check_syntax(full_path)
        if syntax_errors:
            errors.extend(syntax_errors)
            # If syntax errors, skip other checks
            return {
                "success": False,
                "errors": errors,
                "warnings": warnings
            }
        
        # Step 2: Run flake8
        flake8_errors, flake8_warnings = await self._run_flake8(full_path)
        errors.extend(flake8_errors)
        warnings.extend(flake8_warnings)
        
        return {
            "success": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    async def _check_syntax(self, file_path: Path) -> List[str]:
        """Check Python syntax.
        
        Args:
            file_path: Path to Python file
            
        Returns:
            List of syntax error messages
        """
        errors = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            # Try to parse as AST
            ast.parse(code)
            logger.debug(f"Syntax check passed for {file_path.name}")
        
        except SyntaxError as e:
            error_msg = f"Syntax error at line {e.lineno}: {e.msg}"
            if e.text:
                error_msg += f"\n  {e.text.strip()}"
            errors.append(error_msg)
            logger.warning(f"Syntax error found in {file_path.name}")
        
        except Exception as e:
            errors.append(f"Failed to read file: {str(e)}")
            logger.error(f"Error reading {file_path}: {e}")
        
        return errors
    
    async def _run_flake8(self, file_path: Path) -> tuple[List[str], List[str]]:
        """Run flake8 linter.
        
        Args:
            file_path: Path to Python file
            
        Returns:
            Tuple of (errors, warnings)
        """
        errors = []
        warnings = []
        
        try:
            result = subprocess.run(
                ["flake8", str(file_path), "--format=json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                logger.debug(f"Flake8 passed for {file_path.name}")
                return errors, warnings
            
            # Try to parse JSON output
            try:
                # flake8 doesn't have native JSON output, use pylint format or parse text
                output_lines = result.stdout.strip().split('\n')
                for line in output_lines:
                    if not line.strip():
                        continue
                    
                    # Parse format: filename:line:col: code message
                    parts = line.split(':', 3)
                    if len(parts) >= 4:
                        line_num = parts[1]
                        col = parts[2]
                        message = parts[3].strip()
                        
                        # Determine if error or warning based on code
                        if any(message.startswith(code) for code in ['E', 'F']):
                            errors.append(f"Line {line_num}:{col}: {message}")
                        else:
                            warnings.append(f"Line {line_num}:{col}: {message}")
            
            except Exception as e:
                # Fallback: treat all as warnings
                logger.warning(f"Failed to parse flake8 output: {e}")
                if result.stdout:
                    warnings.append(f"Linter issues:\n{result.stdout}")
        
        except subprocess.TimeoutExpired:
            errors.append("Validation timed out after 10 seconds")
            logger.error(f"Flake8 timeout for {file_path}")
        
        except FileNotFoundError:
            # flake8 not installed
            logger.warning("flake8 not found, skipping linter checks")
        
        except Exception as e:
            logger.error(f"Flake8 error: {e}")
        
        return errors, warnings
