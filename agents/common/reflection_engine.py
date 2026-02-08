"""Reflection engine for agent self-correction.

This module enables agents to reflect on validation feedback and iteratively
improve code quality through multiple attempts.
"""

from typing import Dict, List, Optional
import logging
import re

logger = logging.getLogger(__name__)


class ReflectionEngine:
    """Enables agents to reflect on feedback and self-correct code."""
    
    # Initialize reflection engine for iterative code improvement
    # WHY: Allows agent to learn from validation errors and self-correct
    # max_iterations (int): Maximum improvement cycles before giving up
    # llm_client (LLM): Client for generating reflective analysis and code improvements
    def __init__(self, max_iterations: int = 3, llm_client=None):
        self.max_iterations = max_iterations
        self.llm_client = llm_client
        self.reflection_history: List[Dict] = []
        logger.info(f"ReflectionEngine initialized with max_iterations={max_iterations}")
        
    # Core reflection cycle: analyze failures and generate improved code
    # WHY: Turn validation errors into learning opportunities
    # task (str): Original coding task from user
    # generated_code (str): Most recent code attempt that failed validation
    # feedback (Dict): Validation results with errors/warnings
    # iteration (int): Current attempt number (0-indexed)
    # Returns: Improved code (str) or None if max iterations exceeded
    async def reflect_and_improve(
        self,
        task: str,
        generated_code: str,
        feedback: Dict,
        iteration: int
    ) -> Optional[str]:
        if iteration >= self.max_iterations:
            logger.warning(
                f"Max iterations ({self.max_iterations}) reached without success"
            )
            return None
        
        # Build reflection prompt
        reflection_prompt = self._build_reflection_prompt(
            task, generated_code, feedback, iteration
        )
        
        # Get LLM reflection
        logger.info(f"Generating reflection for iteration {iteration}")
        try:
            if self.llm_client is None:
                logger.error("LLM client not configured")
                return None
                
            reflection_response = await self.llm_client.generate(reflection_prompt)
        except Exception as e:
            logger.error(f"Failed to generate reflection: {e}")
            return None
        
        # Store in memory
        self.reflection_history.append({
            "iteration": iteration,
            "feedback": feedback,
            "reflection": reflection_response
        })
        
        # Extract improved code from response
        improved_code = self._extract_code(reflection_response)
        
        if improved_code:
            logger.info(f"Reflection iteration {iteration} complete, generated improved code")
        else:
            logger.warning(f"Failed to extract code from reflection response")
        
        return improved_code
    
    # Build prompt that guides LLM to analyze failure and propose fixes
    # WHY: Provide context and structure for effective self-correction
    # task (str): User's original request
    # code (str): Failed code attempt
    # feedback (Dict): Error details from validator
    # iteration (int): Attempt number for context
    # Returns: Formatted prompt (str) for LLM
    def _build_reflection_prompt(
        self,
        task: str,
        code: str,
        feedback: Dict,
        iteration: int
    ) -> str:
            
        Returns:
            Formatted prompt string
        """
        # Include previous reflections for context
        history_context = ""
        if len(self.reflection_history) > 0:
            history_context = "\n\n## Previous Attempts:\n"
            for entry in self.reflection_history:
                summary = entry["reflection"].get("summary", "No summary")
                history_context += f"- Iteration {entry['iteration']}: {summary}\n"
        
        prompt = f"""You are a software engineer reviewing code that failed validation.

## Original Task
{task}

## Your Previous Attempt (Iteration {iteration + 1})
```python
{code}
```

## Feedback Received
{self._format_feedback(feedback)}
{history_context}

## Reflection Instructions
1. **Analyze**: What went wrong and why?
2. **Learn**: What pattern or principle was violated?
3. **Improve**: Generate corrected code that addresses all issues
4. **Explain**: Briefly explain the key changes made

Provide your improved code in a Python code block.
"""
        return prompt
    
    def _format_feedback(self, feedback: Dict) -> str:
        """Format feedback for prompt.
        
        Args:
            feedback: Dict with success, errors, warnings
            
        Returns:
            Formatted feedback string
        """
        lines = []
        
        if not feedback.get("success", False):
            if "errors" in feedback and feedback["errors"]:
                lines.append("**Errors:**")
                for error in feedback["errors"]:
                    lines.append(f"  - {error}")
            
            if "warnings" in feedback and feedback["warnings"]:
                lines.append("\n**Warnings:**")
                for warning in feedback["warnings"]:
                    lines.append(f"  - {warning}")
        
        return "\n".join(lines) if lines else "No specific errors reported."
    
    def _extract_code(self, llm_response: str) -> Optional[str]:
        """Extract code block from LLM response.
        
        Args:
            llm_response: Raw LLM response
            
        Returns:
            Extracted code or None
        """
        # Try to extract Python code block
        pattern = r"```python\n(.*?)\n```"
        match = re.search(pattern, llm_response, re.DOTALL)
        
        if match:
            return match.group(1).strip()
        
        # Fallback: try plain code block
        pattern = r"```\n(.*?)\n```"
        match = re.search(pattern, llm_response, re.DOTALL)
        
        if match:
            return match.group(1).strip()
        
        # Last resort: return entire response if it looks like code
        if "def " in llm_response or "class " in llm_response:
            logger.warning("No code block found, returning entire response")
            return llm_response.strip()
        
        return None
    
    def get_reflection_summary(self) -> Dict:
        """Get summary of all reflections for this job.
        
        Returns:
            Dict with total_iterations and reflections list
        """
        return {
            "total_iterations": len(self.reflection_history),
            "reflections": self.reflection_history
        }
    
    def reset(self):
        """Reset reflection history for new job."""
        self.reflection_history = []
        logger.debug("Reflection history reset")
