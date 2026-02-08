"""Checker Agent - Code audit and security scanning agent."""

import os
import sys
import httpx
import logging
import subprocess
import json
from pathlib import Path
from typing import Dict, List

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CheckerAgent:
    """Checker agent that audits generated code."""
    
    def __init__(self, job_id: str, task: str, callback_url: str):
        self.job_id = job_id
        self.task = task
        self.callback_url = callback_url
        self.workspace = Path("/workspace")
        self.audit_report = {
            "job_id": job_id,
            "static_analysis": {},
            "security_scan": {},
            "logic_verification": {},
            "summary": ""
        }
    
    async def run(self):
        """Main audit execution."""
        logger.info(f"Checker Agent started for job {self.job_id}")
        
        try:
            # PHASE 1: Static Analysis
            await self.report_progress("Running static analysis...")
            await self.run_static_analysis()
            
            # PHASE 2: Security Scanning
            await self.report_progress("Running security scans...")
            await self.run_security_scan()
            
            # PHASE 3: Logic Verification
            await self.report_progress("Verifying logic against task...")
            await self.verify_logic()
            
            # PHASE 4: Generate summary
            self.generate_summary()
            
            # PHASE 5: Send audit report
            await self.send_audit_report()
            logger.info("Checker Agent completed successfully")
        
        except Exception as e:
            logger.error(f"Checker Agent failed: {e}")
            await self.signal_error(str(e))
            sys.exit(1)
    
    async def run_static_analysis(self):
        """Run linters and static analysis tools."""
        results = {}
        
        # Find all Python files
        python_files = list(self.workspace.rglob("*.py"))
        
        if python_files:
            # Run flake8
            flake8_issues = self.run_flake8(python_files)
            results['flake8'] = flake8_issues
            
            # Run pylint
            pylint_score = self.run_pylint(python_files)
            results['pylint'] = pylint_score
        else:
            results['message'] = "No Python files found in workspace"
        
        self.audit_report['static_analysis'] = results
        logger.info(f"Static analysis complete: {len(results)} tools run")
    
    def run_flake8(self, files: List[Path]) -> Dict:
        """Run flake8 linter."""
        try:
            result = subprocess.run(
                ["flake8"] + [str(f) for f in files],
                capture_output=True,
                text=True,
                cwd=self.workspace
            )
            
            issues = result.stdout.strip().split('\n') if result.stdout else []
            return {
                "issues_count": len([i for i in issues if i]),
                "issues": issues[:10]  # Top 10 issues
            }
        except Exception as e:
            logger.error(f"Flake8 failed: {e}")
            return {"error": str(e)}
    
    def run_pylint(self, files: List[Path]) -> Dict:
        """Run pylint."""
        try:
            result = subprocess.run(
                ["pylint"] + [str(f) for f in files] + ["--output-format=json"],
                capture_output=True,
                text=True,
                cwd=self.workspace
            )
            
            # Pylint returns non-zero for any issues, so we don't check returncode
            try:
                output = json.loads(result.stdout) if result.stdout else []
                score_line = [line for line in result.stderr.split('\n') if 'rated at' in line.lower()]
                score = score_line[0] if score_line else "N/A"
                
                return {
                    "score": score,
                    "issues_count": len(output),
                    "top_issues": output[:5]
                }
            except json.JSONDecodeError:
                return {"error": "Failed to parse pylint output"}
        
        except Exception as e:
            logger.error(f"Pylint failed: {e}")
            return {"error": str(e)}
    
    async def run_security_scan(self):
        """Run security scanning tools."""
        results = {}
        
        # Run bandit  (Python security linter)
        python_files = list(self.workspace.rglob("*.py"))
        
        if python_files:
            bandit_results = self.run_bandit(python_files)
            results['bandit'] = bandit_results
        
        # TODO: Run trufflehog for secret detection
        
        self.audit_report['security_scan'] = results
        logger.info("Security scan complete")
    
    def run_bandit(self, files: List[Path]) -> Dict:
        """Run bandit security linter."""
        try:
            result = subprocess.run(
                ["bandit", "-f", "json"] + [str(f) for f in files],
                capture_output=True,
                text=True,
                cwd=self.workspace
            )
            
            try:
                output = json.loads(result.stdout) if result.stdout else {}
                return {
                    "high_severity": len([r for r in output.get('results', []) if r.get('issue_severity') == 'HIGH']),
                    "medium_severity": len([r for r in output.get('results', []) if r.get('issue_severity') == 'MEDIUM']),
                    "low_severity": len([r for r in output.get('results', []) if r.get('issue_severity') == 'LOW']),
                    "issues": output.get('results', [])[:5]
                }
            except json.JSONDecodeError:
                return {"error": "Failed to parse bandit output"}
        
        except Exception as e:
            logger.error(f"Bandit failed: {e}")
            return {"error": str(e)}
    
    async def verify_logic(self):
        """Verify that generated code matches the task requirements."""
        # TODO: Use LLM to compare code against task description
        # For now, basic file checks
        
        files_created = list(self.workspace.rglob("*"))
        files_created = [f for f in files_created if f.is_file()]
        
        self.audit_report['logic_verification'] = {
            "files_created": len(files_created),
            "file_list": [f.name for f in files_created]
        }
        logger.info(f"Logic verification: {len(files_created)} files created")
    
    def generate_summary(self):
        """Generate human-readable summary of audit."""
        static = self.audit_report['static_analysis']
        security = self.audit_report['security_scan']
        logic = self.audit_report['logic_verification']
        
        issues = []
        
        # Check static analysis
        if 'flake8' in static and static['flake8'].get('issues_count', 0) > 0:
            issues.append(f"Flake8 found {static['flake8']['issues_count']} style issues")
        
        # Check security
        if 'bandit' in security:
            high = security['bandit'].get('high_severity', 0)
            if high > 0:
                issues.append(f"⚠️ Bandit found {high} HIGH severity security issues")
        
        if issues:
            self.audit_report['summary'] = "Issues found: " + "; ".join(issues)
        else:
            self.audit_report['summary'] = "✅ No major issues detected"
        
        logger.info(f"Audit summary: {self.audit_report['summary']}")
    
    async def report_progress(self, current_tool: str):
        """Report progress to orchestrator."""
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    self.callback_url,
                    json={"current_tool": current_tool},
                    timeout=5.0
                )
        except Exception as e:
            logger.warning(f"Failed to report progress: {e}")
    
    async def send_audit_report(self):
        """Send complete audit report to orchestrator."""
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    self.callback_url,
                    json={
                        "audit_report": self.audit_report,
                        "status": "completed"
                    },
                    timeout=10.0
                )
                logger.info("Audit report sent to orchestrator")
        except Exception as e:
            logger.error(f"Failed to send audit report: {e}")
    
    async def signal_error(self, error_message: str):
        """Signal error to orchestrator."""
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    self.callback_url,
                    json={
                        "status": "error",
                        "error": error_message
                    },
                    timeout=5.0
                )
        except Exception as e:
            logger.error(f"Failed to signal error: {e}")


async def main():
    """Entry point for Checker agent."""
    job_id = os.environ.get("JOB_ID")
    task = os.environ.get("TASK")
    callback_url = os.environ.get("ORCHESTRATOR_CALLBACK")
    
    if not all([job_id, task, callback_url]):
        logger.error("Missing required environment variables")
        sys.exit(1)
    
    agent = CheckerAgent(job_id, task, callback_url)
    await agent.run()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
