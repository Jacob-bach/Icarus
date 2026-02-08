"""Test execution component for Builder agent.

This module executes pytest tests and parses results to drive test-driven
development workflows.
"""

import subprocess
import re
from pathlib import Path
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class TestExecutor:
    """Executes pytest tests and parses results."""
    
    def __init__(self, workspace_path: str = "/workspace"):
        """Initialize test executor.
        
        Args:
            workspace_path: Path to workspace directory
        """
        self.workspace = Path(workspace_path)
        logger.info(f"TestExecutor initialized with workspace: {workspace_path}")
    
    async def run_pytest(self, test_file: str, timeout: int = 60) -> Dict:
        """Run pytest on provided test file.
        
        Args:
            test_file: Relative path to test file within workspace
            timeout: Timeout in seconds (default: 60)
            
        Returns:
            Dict with:
                - success (bool): True if all tests passed
                - passed (int): Number of passed tests
                - failed (int): Number of failed tests
                - errors (List[str]): Error messages from failed tests
                - summary (str): Human-readable summary
        """
        test_path = self.workspace / test_file
        
        if not test_path.exists():
            return {
                "success": False,
                "passed": 0,
                "failed": 0,
                "errors": [f"Test file not found: {test_file}"],
                "summary": "Test file not found"
            }
        
        logger.info(f"Running pytest on {test_file}")
        
        try:
            result = subprocess.run(
                ["pytest", str(test_path), "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self.workspace)
            )
            
            # Parse pytest output
            return self._parse_pytest_output(result.stdout, result.stderr, result.returncode)
        
        except subprocess.TimeoutExpired:
            logger.error(f"Test execution timed out after {timeout}s")
            return {
                "success": False,
                "passed": 0,
                "failed": 0,
                "errors": [f"Test execution timed out ({timeout}s limit)"],
                "summary": "TIMEOUT"
            }
        
        except FileNotFoundError:
            logger.error("pytest not found in container")
            return {
                "success": False,
                "passed": 0,
                "failed": 0,
                "errors": ["pytest not installed"],
                "summary": "pytest not found"
            }
        
        except Exception as e:
            logger.error(f"Test execution failed: {e}")
            return {
                "success": False,
                "passed": 0,
                "failed": 0,
                "errors": [f"Test execution failed: {str(e)}"],
                "summary": "ERROR"
            }
    
    def _parse_pytest_output(
        self,
        stdout: str,
        stderr: str,
        return_code: int
    ) -> Dict:
        """Parse pytest output to extract results.
        
        Args:
            stdout: Standard output from pytest
            stderr: Standard error from pytest
            return_code: Exit code from pytest
            
        Returns:
            Dict with parsed results
        """
        passed = 0
        failed = 0
        errors = []
        
        # Look for summary line like "5 passed, 2 failed in 1.23s"
        summary_pattern = r"(\d+)\s+passed"
        match = re.search(summary_pattern, stdout)
        if match:
            passed = int(match.group(1))
        
        failed_pattern = r"(\d+)\s+failed"
        match = re.search(failed_pattern, stdout)
        if match:
            failed = int(match.group(1))
        
        # If no passed/failed found, count PASSED  and FAILED markers
        if passed == 0 and failed == 0:
            passed = stdout.count(" PASSED")
            failed = stdout.count(" FAILED")
        
        # Extract failure messages
        if failed > 0:
            errors = self._extract_failure_messages(stdout, stderr)
        
        # Build summary
        if return_code == 0:
            summary = f"{passed} passed"
        else:
            summary_parts = []
            if passed > 0:
                summary_parts.append(f"{passed} passed")
            if failed > 0:
                summary_parts.append(f"{failed} failed")
            summary = ", ".join(summary_parts)
        
        logger.info(f"Test results: {summary}")
        
        return {
            "success": return_code == 0 and failed == 0,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "summary": summary
        }
    
    def _extract_failure_messages(self, stdout: str, stderr: str) -> List[str]:
        """Extract detailed failure messages from pytest output.
        
        Args:
            stdout: Standard output
            stderr: Standard error
            
       Returns:
            List of error messages
        """
        errors = []
        
        # Pattern for FAILED test lines
        failed_pattern = r"FAILED\s+(.+?)\s+-\s+(.+?)$"
        for match in re.finditer(failed_pattern, stdout, re.MULTILINE):
            test_name = match.group(1)
            error_msg = match.group(2)
            errors.append(f"{test_name}: {error_msg}")
        
        # Also look for assertion errors in the detailed output
        assertion_pattern = r"AssertionError:\s+(.+?)$"
        for match in re.finditer(assertion_pattern, stdout, re.MULTILINE):
            error_detail = match.group(1)
            if error_detail not in str(errors):  # Avoid duplicates
                errors.append(f"Assertion: {error_detail}")
        
        # If no specific errors found but tests failed, include generic message
        if not errors and ("FAILED" in stdout or stderr):
            errors.append("Tests failed - see logs for details")
        
        return errors[:10]  # Limit to 10 errors to avoid overwhelming output
