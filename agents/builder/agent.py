"""Builder Agent - Autonomous code generation agent with v2.0 capabilities."""

import os
import sys
import httpx
import logging
from pathlib import Path
from typing import Optional

# v2.0 imports
from icarus.agents.common.reflection_engine import ReflectionEngine
from icarus.agents.common.validation_runner import ValidationRunner
from icarus.agents.common.test_executor import TestExecutor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BuilderAgent:
    """Builder agent that executes coding tasks autonomously."""
    
    def __init__(
        self,
        job_id: str,
        task: str,
        callback_url: str,
        test_code: Optional[str] = None,
        project_id: str = "default"
    ):
        self.job_id = job_id
        self.task = task
        self.callback_url = callback_url
        self.workspace = Path("/workspace")
        self.test_code = test_code
        self.project_id = project_id
        self.final_code = None
        
        # v2.0 feature flags
        self._reflection_enabled = os.getenv("ENABLE_REFLECTION", "false").lower() == "true"
        self._tdd_enabled = os.getenv("ENABLE_TDD_INTEGRATION", "false").lower() == "true"
        
        # Initialize v2.0 components if enabled
        if self._reflection_enabled:
            self.reflection_engine = ReflectionEngine(max_iterations=3)
            self.validator = ValidationRunner(str(self.workspace))
            logger.info("Reflection mode enabled")
        else:
            self.reflection_engine = None
            self.validator = None
        
        if self._tdd_enabled and test_code:
            self.test_executor = TestExecutor(str(self.workspace))
            logger.info("TDD mode enabled with user-provided tests")
        else:
            self.test_executor = None
    
    async def run(self):
        """Main execution loop."""
        logger.info(f"Builder Agent started for job {self.job_id}")
        logger.info(f"Task: {self.task}")
        
        try:
            # PHASE 1: Research and Planning
            await self.report_progress("Researching task requirements...")
            # TODO: Use WebAccess MCP to search for documentation
            
            # PHASE 2: Code Generation (with v2.0 enhancements)
            await self.report_progress("Generating code...")
            
            if self.test_executor:
                # TDD workflow: generate code driven by tests
                code = await self.generate_code_with_tdd()
            elif self.reflection_engine:
                # Reflection workflow: iterative improvement
                code = await self.generate_code_with_reflection()
            else:
                # Legacy workflow: single-pass generation
                code = await self.generate_code()
                await self.write_file_to_workspace("generated_code.py", code)
            
            self.final_code = code
            
            # PHASE 5: Signal completion
            await self.signal_completion()
            logger.info("Builder Agent completed successfully")
        
        except Exception as e:
            logger.error(f"Builder Agent failed: {e}")
            await self.signal_error(str(e))
            sys.exit(1)
    
    async def create_sample_file(self):
        """Create a sample file (placeholder for actual implementation)."""
        # This is a simplified example
        # In production, this would use LLM to generate code
        
        sample_code = '''"""Sample generated code."""

def hello_world():
    """A simple hello world function."""
    print("Hello from ICARUS Builder!")
    return "success"

if __name__ == "__main__":
    hello_world()
'''
        
        output_file = self.workspace / "generated_code.py"
        output_file.write_text(sample_code)
        logger.info(f"Created file: {output_file}")
    
    async def generate_code(self) -> str:
        """Generate code (placeholder for LLM integration)."""
        # TODO: Integrate with actual LLM (OpenAI, Anthropic, etc.)
        # For now, return sample code
        logger.info("Generating code (placeholder)")
        return '''"""Generated code."""

def hello_world():
    """A hello world function."""
    print("Hello from ICARUS Builder v2.0!")
    return "success"

if __name__ == "__main__":
    hello_world()
'''
    
    async def generate_code_with_reflection(self) -> str:
        """Generate code with reflection-based iterative improvement."""
        logger.info("Starting reflection-enabled code generation")
        
        iteration = 0
        code = None
        
        while iteration < self.reflection_engine.max_iterations:
            # Generate code (or use improved version from reflection)
            if iteration == 0:
                code = await self.generate_code()
            
            # Write to workspace
            await self.write_file_to_workspace("generated_code.py", code)
            
            # Validate
            feedback = await self.validator.validate_python_code("generated_code.py")
            
            # Report progress
            status = "passed" if feedback["success"] else "failed"
            await self.report_progress(
                f"Validation {status} (iteration {iteration + 1}/{self.reflection_engine.max_iterations})"
            )
            
            if feedback["success"]:
                logger.info(f"Validation successful on iteration {iteration + 1}")
                break  # Success!
            
            # Reflect and improve
            logger.info(f"Iteration {iteration + 1}: Reflecting on errors")
            iteration += 1
            
            improved_code = await self.reflection_engine.reflect_and_improve(
                task=self.task,
                generated_code=code,
                feedback=feedback,
                iteration=iteration
            )
            
            if improved_code is None:
                logger.warning("Max iterations reached, using last attempt")
                break
            
            code = improved_code
        
        return code
    
    async def generate_code_with_tdd(self) -> str:
        """Generate code driven by user-provided tests."""
        logger.info("Starting TDD-enabled code generation")
        
        # Write user-provided tests first
        await self.write_file_to_workspace("test_solution.py", self.test_code)
        
        iteration = 0
        max_tdd_iterations = 3
        code = None
        
        while iteration < max_tdd_iterations:
            # Generate code
            if iteration == 0:
                code = await self.generate_code()
            
            # Write solution
            await self.write_file_to_workspace("solution.py", code)
            
            # Run tests
            test_results = await self.test_executor.run_pytest("test_solution.py")
            
            # Report progress
            await self.report_progress(
                f"Tests: {test_results['passed']} passed, {test_results['failed']} failed"
            )
            
            if test_results["success"]:
                logger.info("All tests passed!")
                break
            
            # Use reflection to improve based on test failures
            iteration += 1
            logger.info(f"TDD iteration {iteration}: Tests failed, reflecting...")
            
            if self.reflection_engine:
                code = await self.reflection_engine.reflect_and_improve(
                    task=self.task,
                    generated_code=code,
                    feedback=test_results,
                    iteration=iteration
                )
                
                if code is None:
                    logger.warning("Reflection failed, using last code attempt")
                    break
        
        return code
    
    async def write_file_to_workspace(self, filename: str, content: str):
        """Write content to a file in the workspace."""
        file_path = self.workspace / filename
        file_path.write_text(content)
        logger.info(f"Wrote file: {file_path}")
    
    async def report_progress(self, current_tool: str):
        """Report current progress to orchestrator."""
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    self.callback_url,
                    json={
                        "current_tool": current_tool,
                        "cpu_usage": 0.0,  # TODO: Get actual usage
                        "ram_usage_mb": 0.0
                    },
                    timeout=5.0
                )
        except Exception as e:
            logger.warning(f"Failed to report progress: {e}")
    
    async def signal_completion(self):
        """Signal to orchestrator that work is complete."""
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    self.callback_url,
                    json={
                        "status": "completed",
                        "message": "Builder agent finished successfully"
                    },
                    timeout=5.0
                )
        except Exception as e:
            logger.error(f"Failed to signal completion: {e}")
    
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
    """Entry point for Builder agent."""
    job_id = os.environ.get("JOB_ID")
    task = os.environ.get("TASK")
    callback_url = os.environ.get("ORCHESTRATOR_CALLBACK")
    
    if not all([job_id, task, callback_url]):
        logger.error("Missing required environment variables")
        sys.exit(1)
    
    agent = BuilderAgent(job_id, task, callback_url)
    await agent.run()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
