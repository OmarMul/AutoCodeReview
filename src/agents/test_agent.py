import json
from typing import Dict, List, Any, Optional, Set

from src.agents.base_agent import (
    BaseAgent,
    AgentType,
    AgentState,
    AgentSuggestion,
    MessageType
)
from src.analyzers.pipeline import FileAnalysis, FunctionAnalysis
from src.llm.groq_client import GroqClient
from src.llm.prompt_templates import (
    get_test_agent_system_prompt,
    build_test_case_prompt
)
from src.utils.logger import get_logger

logger = get_logger(__name__)

class TestAgent(BaseAgent):
    EDGE_CASE_TYPES = [
        "empty_input",       # Empty lists, strings, dicts
        "none_input",        # None values
        "zero_value",        # Zero in numeric operations
        "negative_value",    # Negative numbers
        "boundary_min",      # Minimum boundary values
        "boundary_max",      # Maximum boundary values
        "large_input",       # Very large inputs
        "invalid_type",      # Wrong type inputs
        "exception_cases",   # Error conditions
    ]

    def __init__(
        self,
        llm_client: GroqClient,
        model: str = "llama-3.3-70b-versatile",
        max_tokens: int = 2000,
        min_complexity_for_testing: int = 5,
        target_coverage: float = 0.8
    ):
        super().__init__(
            agent_type=AgentType.TEST,
            llm_client=llm_client,
            model=model,
            max_tokens=max_tokens
        )
        self.min_complexity_for_testing = min_complexity_for_testing
        self.target_coverage = target_coverage
        
        logger.info(
            f"Initialized TestAgent "
            f"(min_complexity={min_complexity_for_testing}, "
            f"target_coverage={target_coverage})"
        )

    def get_system_prompt(self) -> str:
        """Get system prompt for test agent."""
        return get_test_agent_system_prompt()
    

    async def analyze(
        self,
        file_analysis: FileAnalysis,
        context: Optional[Dict[str, Any]] = None
    ) -> AgentState:
        logger.info(f"TestAgent analyzing {file_analysis.filename}")

        self.reset_state()

        try:
            functions_needing_tests = self._identify_functions_needing_tests(
                file_analysis
            )

            if not functions_needing_tests:
                logger.info("All functions appear adequately testable")
                self.state.completed = True
                return self.state
            
            converage_analysis = self._analyze_converage_gaps(
                file_analysis,
                functions_needing_tests
            )
            
            if converage_analysis:
                self.state.add_suggestion(converage_analysis)

            suggestions = await self._generate_test_suggestions(
                file_analysis,
                functions_needing_tests,
            )

            for suggestion in suggestions:
                self.state.add_suggestion(suggestion)

            critical_tests = sum(
                1 for s in self.state.suggestions
                if s.severity in ['high', 'critical']
            )

            self.send_message(
                recipient=None,
                message_type=MessageType.ANALYSIS,
                content=f"Suggested tests for {len(functions_needing_tests)} functions "
                        f"({critical_tests} high priority)",
                metadata={
                    'functions_needing_tests': len(functions_needing_tests),
                    'test_suggestions': len(self.state.suggestions),
                    'edge_case_suggestions': len(edge_case_suggestions)
                }
            )

            self.state.completed = True
            logger.info(
                f"TestAgent completed: {len(self.state.suggestions)} suggestions"
            )
        except Exception as e:
            logger.error(f"TestAgent failed: {e}", exc_info=True)
            self.state.error = str(e)
            self.state.completed = False
        
        return self.state

    def _identify_functions_needing_tests(
        self,
        file_analysis: FileAnalysis
    ) -> List[FunctionAnalysis]:
        """Identify functions that need test cases."""
        needs_tests = []
        for func in file_analysis.functions:
            if func.name.startswith('_') and func.complexity >= self.min_complexity_for_testing:
                continue

            if func.complexity >= self.min_complexity_for_testing:
                needs_tests.append(func)
                logger.debug(
                    f"Function needs tests: {func.name} "
                    f"(complexity={func.complexity})"
                )
            
            if func.has_security_issues:
                needs_tests.append(func)
                logger.debug(
                    f"Function needs tests: {func.name} "
                    f"(security issues detected)"
                )

            if not func.name.startswith('_') and func.complexity >= 3:
                needs_tests.append(func)
                logger.debug(f"Needs tests (public API): {func.name}")
        return needs_tests 

    def _analyze_converage_gaps(
        self,
        file_analysis: FileAnalysis,
        untested_functions: List[FunctionAnalysis]

    ) -> Optional[AgentSuggestion]:
        total_functions = len(untested_functions)
        
        untested_count = len(untested_functions)
        estimated_coverage = ((total_functions - untested_count) / total_functions) * 100
        
        # Calculate complexity-weighted coverage
        total_complexity = sum(f.complexity for f in file_analysis.functions)
        untested_complexity = sum(f.complexity for f in untested_functions)
        weighted_coverage = 0.0
        if total_complexity > 0:
            weighted_coverage = ((total_complexity - untested_complexity) / total_complexity) * 100
        
        # Build coverage report
        description = f"## Test Coverage Analysis\n\n"
        description += f"**Estimated Coverage**: {estimated_coverage:.1f}%\n"
        description += f"**Complexity-Weighted Coverage**: {weighted_coverage:.1f}%\n"
        description += f"**Target Coverage**: {self.target_coverage}%\n\n"
        
        if estimated_coverage < self.target_coverage:
            gap = self.target_coverage - estimated_coverage
            description += f"⚠️ **Coverage Gap**: {gap:.1f}% below target\n\n"
        
        description += f"**Functions Without Tests**: {untested_count}/{total_functions}\n\n"
        
        if untested_functions:
            description += "**High Priority Functions to Test**:\n"
            # Sort by complexity (highest first)
            sorted_funcs = sorted(
                untested_functions,
                key=lambda f: f.complexity,
                reverse=True
            )[:5]  # Top 5
            for func in sorted_funcs:
                description += f"- `{func.name}` (complexity: {func.complexity})\n"
        
        severity = "critical" if estimated_coverage < 50 else \
                   "high" if estimated_coverage < 70 else "medium"
        
        return AgentSuggestion(
            agent_type=self.agent_type,
            suggestion_type="coverage_analysis",
            title="Test Coverage Analysis",
            description=description,
            severity=severity,
            confidence=0.9,
            rationale=f"Current coverage ({estimated_coverage:.1f}%) below target ({self.target_coverage}%)"
        )
    def _suggest_edge_cases(
        self,
        functions: List[FunctionAnalysis]
    ) -> List[AgentSuggestion]:
        """
        Suggest edge case testing for functions.
        
        Args:
            functions: Functions to analyze
        
        Returns:
            List of edge case suggestions
        """
        suggestions = []
        
        for func in functions[:3]:  # Limit to top 3 functions
            # Determine relevant edge cases based on function signature
            relevant_edge_cases = self._identify_relevant_edge_cases(func)
            
            if not relevant_edge_cases:
                continue
            
            description = f"## Edge Cases for `{func.name}`\n\n"
            description += f"Consider testing these edge cases:\n\n"
            
            for edge_case in relevant_edge_cases:
                description += f"### {edge_case['name']}\n"
                description += f"{edge_case['description']}\n\n"
                description += f"```python\n{edge_case['example']}\n```\n\n"
            
            suggestion = AgentSuggestion(
                agent_type=self.agent_type,
                suggestion_type="edge_cases",
                title=f"Edge Cases: {func.name}",
                description=description,
                line_number=func.line_start,
                severity="high" if func.complexity > 10 else "medium",
                confidence=0.85,
                rationale=f"Edge case testing for {func.name}"
            )
            suggestions.append(suggestion)
        
        return suggestions
    
    def _identify_relevant_edge_cases(
        self,
        func: FunctionAnalysis
    ) -> List[Dict[str, str]]:
        """Identify relevant edge cases for a function."""
        edge_cases = []
        
        # Check function arguments to determine relevant edge cases
        has_numeric_args = any('int' in str(arg).lower() or 'float' in str(arg).lower() for arg in func.args)
        has_collection_args = any('list' in str(arg).lower() or 'dict' in str(arg).lower() for arg in func.args)
        has_string_args = any('str' in str(arg).lower() or 'name' in str(arg).lower() for arg in func.args)
        
        # Empty input cases
        if has_collection_args or has_string_args:
            edge_cases.append({
                'name': 'Empty Input',
                'description': 'Test with empty collections or strings',
                'example': f'def test_{func.name}_empty_input():\n    result = {func.name}([])\n    assert result is not None'
            })
        
        # None input
        if func.args:
            edge_cases.append({
                'name': 'None Input',
                'description': 'Test handling of None values',
                'example': f'def test_{func.name}_none_input():\n    with pytest.raises(ValueError):\n        {func.name}(None)'
            })
        
        # Numeric edge cases
        if has_numeric_args:
            edge_cases.append({
                'name': 'Zero Value',
                'description': 'Test with zero as input',
                'example': f'def test_{func.name}_zero():\n    result = {func.name}(0)\n    assert result == expected_value'
            })
            
            edge_cases.append({
                'name': 'Negative Value',
                'description': 'Test with negative numbers',
                'example': f'def test_{func.name}_negative():\n    result = {func.name}(-1)\n    # Verify behavior with negative input'
            })
        
        # Large input
        if has_collection_args:
            edge_cases.append({
                'name': 'Large Input',
                'description': 'Test with large datasets for performance',
                'example': f'def test_{func.name}_large_input():\n    large_list = list(range(10000))\n    result = {func.name}(large_list)\n    # Verify handles large input'
            })
        
        return edge_cases[:3]  # Return top 3 most relevant
    
    def _generate_test_suggestions(
        self,
        file_analysis: FileAnalysis,
        functions_needing_tests: List[FunctionAnalysis]

    ) ->List[AgentSuggestion]:
        """Generate test suggestions using LLM."""
        functions_data = []
        for func in functions_needing_tests:
            functions_data.append({
                'name': func.name,
                'line_start': func.line_start,
                'line_end': func.line_end,
                'complexity': func.complexity,
                'args': func.args,
                'returns': func.returns,
                'docstring': func.docstring,
                'is_async': func.is_async
            })

        prompt = build_test_case_prompt(
            code=file_analysis.source_code,
            language="python",
            file_name=file_analysis.filename,
            functions=functions_data,
            max_complexity=file_analysis.max_complexity
        )

        try:
            response = await self.call_llm(prompt)
            suggestions = self._parse_test_suggestions(response)
            return suggestions
        except Exception as e:
            logger.error(f"Failed to generate test suggestions: {e}")
            return []

    def _parse_test_response(
        self,
        response: str
    ) -> List[AgentSuggestion]:
        """Parse JSON response from LLM."""
        suggestions = []
        
        try:
            # Extract JSON from response
            json_str = self._extract_json(response)
            data = json.loads(json_str)
            
            # Parse test cases
            for test_case in data.get('test_cases', []):
                func_name = test_case.get('function', 'unknown')
                test_name = test_case.get('test_name', f'test_{func_name}')
                test_type = test_case.get('test_type', 'normal')
                
                # Build description
                description = f"**Test Case**: `{test_name}`\n\n"
                description += f"**Type**: {test_type}\n"
                description += f"**Description**: {test_case.get('description', '')}\n\n"
                
                if test_case.get('input'):
                    description += f"**Input**: `{test_case['input']}`\n"
                if test_case.get('expected_output'):
                    description += f"**Expected Output**: `{test_case['expected_output']}`\n\n"
                
                # Add pytest code if available
                if test_case.get('pytest_code'):
                    description += f"**Pytest Code**:\n```python\n{test_case['pytest_code']}\n```\n"
                
                # Determine severity based on test type
                severity_map = {
                    'error': 'high',
                    'edge': 'high',
                    'integration': 'medium',
                    'normal': 'medium'
                }
                severity = severity_map.get(test_type, 'medium')
                
                suggestion = AgentSuggestion(
                    agent_type=self.agent_type,
                    suggestion_type='test_case',
                    title=f"Add test: {test_name}",
                    description=description,
                    code_snippet=test_case.get('pytest_code'),
                    severity=severity,
                    confidence=0.85,
                    rationale=f"Test coverage for {func_name}: {test_type} case"
                )
                suggestions.append(suggestion)
        
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            # Create a general suggestion with the full response
            if response.strip():
                suggestion = AgentSuggestion(
                    agent_type=self.agent_type,
                    suggestion_type='test_case',
                    title="Test Coverage Suggestions",
                    description=response.strip(),
                    severity='medium',
                    confidence=0.7,
                    rationale="General test coverage recommendations"
                )
                suggestions.append(suggestion)
        
        return suggestions
    
    def _extract_json(self, response: str) -> str:
        """Extract JSON from LLM response."""
        # Try to find JSON block
        if '```json' in response:
            parts = response.split('```json')
            if len(parts) > 1:
                json_part = parts[1].split('```')[0]
                return json_part.strip()
        
        # Try to find { ... } block
        start = response.find('{')
        end = response.rfind('}')
        
        if start != -1 and end != -1:
            return response[start:end+1]
        
        return response