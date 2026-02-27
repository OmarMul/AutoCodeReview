from typing import Dict, List, Any, Optional
import json
from src.agents.base_agent import (
    BaseAgent,
    AgentType,
    AgentState,
    AgentSuggestion,
    MessageType
)
from src.analyzers.pipeline import FileAnalysis, FunctionAnalysis
from src.llm.groq_client import GroqClient
from src.utils.logger import get_logger
from src.llm.prompt_templates import (
    get_code_analyzer_system_prompt,
    build_code_analysis_prompt
)

logger = get_logger(__name__)

class CodeAnalyzerAgent(BaseAgent):
    """
    Code Quality and Structure Analysis Agent.
    """
    def __init__(self, llm_client: GroqClient, model: str = "llama-3.3-70b-versatile", max_tokens: int = 2000, complexity_threshold: int = 10):
        super().__init__(
            agent_type=AgentType.CODE_ANALYZER,
            llm_client=llm_client,
            model=model,
            max_tokens=max_tokens
        )
        self.complexity_threshold = complexity_threshold

        logger.info(f"CodeAnalyzerAgent initialized with complexity threshold: {self.complexity_threshold}")
    
    def get_system_prompt(self) -> str:
        """Get system prompt for code analyzer agent."""
        return get_code_analyzer_system_prompt()

    async def analyze(
        self,
        file_analysis: FileAnalysis,
        context: Optional[Dict[str, Any]]
    ) -> AgentState:
        """
        Analyze code and generate suggestions.
        """

        logger.info(f"Analyzing file: {file_analysis.filename}")

        self.reset_state()

        try:
            #1. Identify functions needing attention
            complex_functions = self._identify_complex_functions(file_analysis)

            if not complex_functions:
                logger.info("No complex functions found")
                functions_to_analyze = file_analysis.functions[:5]
            else:
                functions_to_analyze = complex_functions

            #2. Analyze each function with llm
            for func in functions_to_analyze:
                logger.info(f"Analyzing function: {func.name}")
                suggestions = await self._analyze_function(func, file_analysis)
                for suggestion in suggestions:
                    self.state.add_suggestion(suggestion)
            
            #3. Analyze overall file structure
            if len(file_analysis.functions) > 10:
                logger.info("Analyzing file structure")
                structure_suggestion = await self._analyze_file_structure(file_analysis)
                for suggestion in structure_suggestion:
                    self.state.add_suggestion(suggestion)

            
            #4. Set completed status
            self.send_message(
                recipient=None,  # Broadcast
                message_type=MessageType.ANALYSIS,
                content=f"Found {len(self.state.suggestions)} code quality issues",
                metadata={
                    'complex_functions': len(complex_functions),
                    'total_analyzed': len(functions_to_analyze)
                }
            )

            self.state.completed = True
            logger.info(f"Analysis completed for {file_analysis.filename}")

        
        except Exception as e:
            logger.error(f"Error analyzing file {file_analysis.filename}: {e}")
            self.state.set_completed(True)
            self.state.error = str(e)
        
        return self.state

    def _identify_complex_functions(
        self,
        file_analysis: FileAnalysis
    ) -> List[FunctionAnalysis]:
        """
        Identify functions that need attention based on complexity.
        """
        complex_functions = []
        for func in file_analysis.functions:
            if func.complexity > self.complexity_threshold:
                complex_functions.append(func)
                logger.debug(
                    f"Flagged complex function: {func.name} "
                    f"(complexity={func.complexity})"
                )
        return complex_functions
    
    async def _analyze_function(
        self,
        func: FunctionAnalysis,
        file_analysis: FileAnalysis
    ) -> List[AgentSuggestion]:
        """
        Analyze a single function using LLM.
        """
        prompt = self._build_function_analysis_prompt(func, file_analysis)
        
        #call llm
        try:
            response = await self.call_llm(prompt)
            suggestions = self._parse_function_analysis_response(response, func)
            return suggestions
        except Exception as e:
            logger.error(f"Error analyzing function {func.name}: {e}")
            return []
    def _build_function_analysis_prompt(
        self,
        func: FunctionAnalysis,
        file_analysis: FileAnalysis
    ) -> str:
        """Build analysis prompt using Jinja2 template."""
        # Prepare function data for template
        functions_data = []
        for f in file_analysis.functions:
            functions_data.append({
                'name': f.name,
                'line_start': f.line_start,
                'line_end': f.line_end,
                'complexity': f.complexity,
                'rank': f.complexity_rank,
                'docstring': f.docstring,
                'is_complex': f.is_complex,
                'args': f.args
            })
        
        # Build prompt with template
        prompt = build_code_analysis_prompt(
            code=file_analysis.source_code,
            language="python",
            file_name=file_analysis.filename,
            total_functions=file_analysis.total_functions,
            avg_complexity=file_analysis.average_complexity,
            max_complexity=file_analysis.max_complexity,
            maintainability_index=file_analysis.maintainability_index,
            functions=functions_data
        )
        
        return prompt

    def _parse_function_analysis_response(
        self,
        response: str,
        func: FunctionAnalysis
    ) -> List[AgentSuggestion]:
        """Parse JSON response from LLM."""
        suggestions = []
        
        try:
            # Try to parse JSON
            data = json.loads(response)
            
            # Parse issues
            for issue in data.get('issues', []):
                suggestion = AgentSuggestion(
                    agent_type=self.agent_type,
                    suggestion_type=issue.get('type', 'refactor'),
                    title=f"{issue.get('type', 'Issue').title()}: {issue.get('description', '')[:50]}...",
                    description=issue.get('description', ''),
                    line_number=issue.get('line'),
                    severity=issue.get('severity', 'medium'),
                    confidence=0.8,
                    rationale=f"Code analysis finding"
                )
                suggestions.append(suggestion)
            
            # Parse suggestions
            for sugg in data.get('suggestions', []):
                suggestion = AgentSuggestion(
                    agent_type=self.agent_type,
                    suggestion_type='refactor',
                    title=sugg.get('title', 'Code Improvement'),
                    description=f"{sugg.get('reason', '')}\n\nSuggested code:\n```python\n{sugg.get('suggested_code', '')}\n```",
                    code_snippet=sugg.get('suggested_code'),
                    line_number=sugg.get('line'),
                    severity='medium',
                    confidence=0.85,
                    rationale=sugg.get('reason', '')
                )
                suggestions.append(suggestion)
        
        except json.JSONDecodeError:
            # Fallback to text parsing if JSON fails
            logger.warning("Failed to parse JSON response, using fallback")
            suggestions = self._fallback_parse(response, func)
        
        return suggestions

    def _fallback_parse(
        self,
        response: str,
        func: FunctionAnalysis
    ) -> List[AgentSuggestion]:
        """Fallback parser when JSON parsing fails."""
        # Create a single suggestion with the full response
        suggestion = AgentSuggestion(
            agent_type=self.agent_type,
            suggestion_type='refactor',
            title=f"Code Quality Issues in {func.name}",
            description=response.strip(),
            line_number=func.line_start,
            severity='medium',
            confidence=0.6,
            rationale=f"Function has complexity {func.complexity}"
        )
        return [suggestion]

    async def _analyze_file_structure(
        self,
        file_analysis: FileAnalysis
    ) -> List[AgentSuggestion]:
        """
        Analyze overall file structure and organization.
        
        Args:
            file_analysis: File analysis results
        
        Returns:
            List of suggestions
        """
        prompt_parts = [
            f"Analyze the overall structure of this Python file:",
            "",
            f"File: {file_analysis.filename}",
            f"Total Functions: {len(file_analysis.functions)}",
            f"Total Classes: {len(file_analysis.classes)}",
            f"Average Complexity: {file_analysis.average_complexity:.1f}",
            f"Max Complexity: {file_analysis.max_complexity}",
            f"Maintainability Index: {file_analysis.maintainability_index:.1f}/100",
            "",
            "Functions:",
        ]
        
        # List all functions with complexity
        for func in file_analysis.functions[:10]:  # Limit to 10
            prompt_parts.append(
                f"- {func.name}: complexity {func.complexity}, "
                f"{'documented' if func.docstring else 'undocumented'}"
            )
        
        prompt_parts.extend([
            "",
            "Please identify:",
            "1. Structural issues (e.g., file too large, poor organization)",
            "2. Opportunities to split into multiple files/modules",
            "3. Missing abstractions or patterns",
            "4. Overall architectural improvements",
            "",
            "Be specific and prioritize the most impactful suggestions."
        ])
        
        try:
            response = await self.call_llm("\n".join(prompt_parts))
            
            # Create a single structural suggestion
            suggestion = AgentSuggestion(
                agent_type=self.agent_type,
                suggestion_type="architecture",
                title="File Structure Improvements",
                description=response.strip(),
                severity="medium",
                confidence=0.7,
                rationale=f"File has {len(file_analysis.functions)} functions with average complexity {file_analysis.average_complexity:.1f}"
            )
            
            return [suggestion]
        
        except Exception as e:
            logger.error(f"Failed to analyze file structure: {e}")
            return []