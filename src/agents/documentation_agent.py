import json
from typing import Dict, List, Any, Optional

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
    get_documentation_agent_system_prompt,
    build_documentation_prompt
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DocumentationAgent(BaseAgent):
    """
    Documentation Quality Analysis Agent.
    
    Responsibilities:
    - Identify undocumented functions, classes, and modules
    - Generate comprehensive docstrings following PEP 257
    - Add type hints for better IDE support
    - Document parameters, return values, and exceptions
    - Provide usage examples for complex functions
    - Flag misleading or outdated documentation
    """
    
    def __init__(
        self,
        llm_client: GroqClient,
        model: str = "llama-3.3-70b-versatile",
        max_tokens: int = 2500
    ):
        """
        Initialize Documentation Agent.
        
        Args:
            llm_client: Groq LLM client
            model: Model to use
            max_tokens: Max tokens in response
        """
        super().__init__(
            agent_type=AgentType.DOCUMENTATION,
            llm_client=llm_client,
            model=model,
            max_tokens=max_tokens
        )
        
        logger.info("Initialized DocumentationAgent")
    
    def get_system_prompt(self) -> str:
        """Get system prompt for documentation agent."""
        return get_documentation_agent_system_prompt()
    
    async def analyze(
        self,
        file_analysis: FileAnalysis,
        context: Optional[Dict[str, Any]] = None
    ) -> AgentState:
        """
        Analyze documentation quality and generate improvements.
        
        Args:
            file_analysis: Complete file analysis from pipeline
            context: Additional context from other agents
        
        Returns:
            AgentState with documentation suggestions
        """
        logger.info(f"DocumentationAgent analyzing {file_analysis.filename}")
        
        # Reset state
        self.reset_state()
        
        try:
            # 1. Identify undocumented functions
            undocumented = self._identify_undocumented(file_analysis)
            
            if not undocumented:
                logger.info("All functions are documented")
                self.state.completed = True
                return self.state
            
            # 2. Gather findings from other agents (if available in context)
            past_findings = self._gather_past_findings(context)
            
            # 3. Analyze with LLM using Jinja2 template
            suggestions = await self._analyze_with_llm(
                file_analysis,
                undocumented,
                past_findings
            )
            
            for suggestion in suggestions:
                self.state.add_suggestion(suggestion)
            
            # 4. Send summary message
            self.send_message(
                recipient=None,
                message_type=MessageType.ANALYSIS,
                content=f"Generated documentation for {len(undocumented)} undocumented functions",
                metadata={
                    'undocumented_count': len(undocumented),
                    'suggestions_count': len(self.state.suggestions)
                }
            )
            
            self.state.completed = True
            logger.info(
                f"DocumentationAgent completed: {len(self.state.suggestions)} suggestions"
            )
        
        except Exception as e:
            logger.error(f"DocumentationAgent failed: {e}", exc_info=True)
            self.state.error = str(e)
            self.state.completed = False
        
        return self.state
    
    def _identify_undocumented(
        self,
        file_analysis: FileAnalysis
    ) -> List[FunctionAnalysis]:
        """
        Identify functions without proper documentation.
        
        Args:
            file_analysis: File analysis results
        
        Returns:
            List of undocumented functions
        """
        undocumented = []
        
        for func in file_analysis.functions:
            # Flag if no docstring or very short docstring
            if not func.docstring or len(func.docstring.strip()) < 10:
                undocumented.append(func)
                logger.debug(f"Undocumented function: {func.name}")
            
            # Also flag complex functions with minimal documentation
            elif func.complexity > 10 and len(func.docstring.strip()) < 50:
                undocumented.append(func)
                logger.debug(
                    f"Complex function with minimal docs: {func.name} "
                    f"(complexity={func.complexity})"
                )
        
        return undocumented
    
    def _gather_past_findings(
        self,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """
        Gather findings from other agents to include in documentation.
        
        Args:
            context: Context from other agents
        
        Returns:
            Formatted string of past findings
        """
        if not context:
            return ""
        
        findings = []
        
        # Extract findings from context
        if 'security_concerns' in context:
            findings.append("**Security Concerns**:")
            for concern in context['security_concerns']:
                findings.append(f"- {concern}")
        
        if 'complexity_issues' in context:
            findings.append("\n**Complexity Issues**:")
            for issue in context['complexity_issues']:
                findings.append(f"- {issue}")
        
        if 'performance_notes' in context:
            findings.append("\n**Performance Notes**:")
            for note in context['performance_notes']:
                findings.append(f"- {note}")
        
        return "\n".join(findings) if findings else ""
    
    async def _analyze_with_llm(
        self,
        file_analysis: FileAnalysis,
        undocumented: List[FunctionAnalysis],
        past_findings: str
    ) -> List[AgentSuggestion]:
        """Generate documentation using LLM with Jinja2 template."""
        
        # Prepare functions data for template
        functions_data = []
        for func in undocumented:
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
        
        # Build prompt using Jinja2 template
        prompt = build_documentation_prompt(
            code=file_analysis.source_code,
            language="python",
            file_name=file_analysis.filename,
            functions=functions_data,
            past_findings=past_findings
        )
        
        try:
            # Call LLM
            response = await self.call_llm(prompt)
            
            # Parse JSON response
            suggestions = self._parse_documentation_response(response)
            
            return suggestions
        
        except Exception as e:
            logger.error(f"Failed to generate documentation: {e}")
            return []
    
    def _parse_documentation_response(
        self,
        response: str
    ) -> List[AgentSuggestion]:
        """Parse JSON response from LLM."""
        suggestions = []
        
        try:
            # Extract JSON from response
            json_str = self._extract_json(response)
            data = json.loads(json_str)
            
            # Parse documentation suggestions
            for doc in data.get('documentation', []):
                doc_type = doc.get('type', 'function')
                name = doc.get('name', 'unknown')
                docstring = doc.get('docstring', '')
                
                # Build description
                description = f"**Suggested Documentation for `{name}`**:\n\n"
                description += "```python\n"
                
                # Add function signature if function
                if doc_type == 'function':
                    description += f"def {name}(...):\n"
                    description += f'    """{docstring}"""\n'
                else:
                    description += f'"""{docstring}"""\n'
                
                description += "```\n\n"
                
                if doc.get('includes_example'):
                    description += "✓ Includes usage example\n"
                
                suggestion = AgentSuggestion(
                    agent_type=self.agent_type,
                    suggestion_type='documentation',
                    title=f"Add documentation for {name}",
                    description=description,
                    code_snippet=docstring,
                    line_number=doc.get('line'),
                    severity='medium' if doc_type == 'function' else 'low',
                    confidence=0.9,
                    rationale=f"Missing or insufficient documentation for {doc_type}"
                )
                suggestions.append(suggestion)
        
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            # Create a general suggestion with the full response
            if response.strip():
                suggestion = AgentSuggestion(
                    agent_type=self.agent_type,
                    suggestion_type='documentation',
                    title="Documentation Improvements",
                    description=response.strip(),
                    severity='medium',
                    confidence=0.7,
                    rationale="General documentation suggestions"
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