"""
Style Agent - Enforces code style and formatting standards with auto-fix capabilities.
Specializes in PEP 8, naming conventions, and Python best practices.
"""

import json
import logging
import yaml
from pathlib import Path
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
from src.agents.prompts import (
    get_style_agent_system_prompt,
    build_style_check_prompt
)

logger = logging.getLogger(__name__)


class StyleAgent(BaseAgent):
    """
    Code Style and Formatting Agent.
    
    Responsibilities:
    - Check PEP 8 compliance
    - Verify consistent naming conventions
    - Identify non-Pythonic code
    - Suggest modern Python features
    - Check import organization
    - Flag readability issues
    - Provide auto-fix suggestions where possible
    """
    
    def __init__(
        self,
        llm_client: GroqClient,
        model: str = "llama-3.3-70b-versatile",
        max_tokens: int = 2000,
        style_guide: str = "PEP 8",
        rules_config_path: str = "config/style_rules.yaml"
    ):
        """
        Initialize Style Agent.
        
        Args:
            llm_client: Groq LLM client
            model: Model to use
            max_tokens: Max tokens in response
            style_guide: Style guide to enforce (default: PEP 8)
            rules_config_path: Path to style rules configuration
        """
        super().__init__(
            agent_type=AgentType.STYLE,
            llm_client=llm_client,
            model=model,
            max_tokens=max_tokens
        )
        self.style_guide = style_guide
        self.rules_config = self._load_rules_config(rules_config_path)
        
        logger.info(f"Initialized StyleAgent (style_guide={style_guide})")
    
    def _load_rules_config(self, config_path: str) -> Dict[str, Any]:
        """Load style rules from YAML configuration."""
        try:
            config_file = Path(config_path)
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config = yaml.safe_load(f)
                logger.info(f"Loaded style rules from {config_path}")
                return config
            else:
                logger.warning(f"Style rules config not found: {config_path}")
                return {}
        except Exception as e:
            logger.error(f"Failed to load style rules: {e}")
            return {}
    
    def get_system_prompt(self) -> str:
        """Get system prompt for style agent."""
        return get_style_agent_system_prompt()
    
    async def analyze(
        self,
        file_analysis: FileAnalysis,
        context: Optional[Dict[str, Any]] = None
    ) -> AgentState:
        """
        Analyze code style and formatting.
        
        Args:
            file_analysis: Complete file analysis from pipeline
            context: Additional context from other agents
        
        Returns:
            AgentState with style suggestions
        """
        logger.info(f"StyleAgent analyzing {file_analysis.filename}")
        
        # Reset state
        self.reset_state()
        
        try:
            # 1. Quick static checks (before LLM)
            static_suggestions = self._perform_static_checks(file_analysis)
            for suggestion in static_suggestions:
                self.state.add_suggestion(suggestion)
            
            # 2. Analyze with LLM using Jinja2 template
            llm_suggestions = await self._analyze_style_with_llm(file_analysis)
            for suggestion in llm_suggestions:
                self.state.add_suggestion(suggestion)
            
            # 3. Add auto-fix suggestions
            auto_fix_suggestions = self._generate_auto_fixes(
                file_analysis,
                self.state.suggestions
            )
            for suggestion in auto_fix_suggestions:
                self.state.add_suggestion(suggestion)
            
            # 4. Send summary message
            auto_fixable = sum(
                1 for s in self.state.suggestions
                if 'auto_fix' in s.metadata
            )
            
            self.send_message(
                recipient=None,
                message_type=MessageType.ANALYSIS,
                content=f"Found {len(self.state.suggestions)} style issues "
                        f"({auto_fixable} auto-fixable)",
                metadata={
                    'style_issues': len(self.state.suggestions),
                    'auto_fixable': auto_fixable,
                    'style_guide': self.style_guide
                }
            )
            
            self.state.completed = True
            logger.info(
                f"StyleAgent completed: {len(self.state.suggestions)} suggestions "
                f"({auto_fixable} auto-fixable)"
            )
        
        except Exception as e:
            logger.error(f"StyleAgent failed: {e}", exc_info=True)
            self.state.error = str(e)
            self.state.completed = False
        
        return self.state
    
    def _perform_static_checks(
        self,
        file_analysis: FileAnalysis
    ) -> List[AgentSuggestion]:
        """
        Perform quick static style checks without LLM.
        
        Args:
            file_analysis: File analysis
        
        Returns:
            List of style suggestions
        """
        suggestions = []
        
        # Check naming conventions
        suggestions.extend(self._check_naming_conventions(file_analysis))
        
        # Check function complexity for documentation requirements
        suggestions.extend(self._check_documentation_requirements(file_analysis))
        
        # Check for modern Python features
        suggestions.extend(self._check_modern_python(file_analysis))
        
        return suggestions
    
    def _check_naming_conventions(
        self,
        file_analysis: FileAnalysis
    ) -> List[AgentSuggestion]:
        """Check naming conventions against rules."""
        suggestions = []
        naming_rules = self.rules_config.get('naming', {})
        
        for func in file_analysis.functions:
            # Check function naming (should be snake_case)
            if not self._is_snake_case(func.name) and not func.name.startswith('_'):
                description = f"Function `{func.name}` does not follow snake_case naming.\n\n"
                description += f"**Rule**: {naming_rules.get('functions', {}).get('description', 'Use snake_case')}\n\n"
                description += f"**Current**: `{func.name}`\n"
                
                # Suggest fix
                suggested_name = self._to_snake_case(func.name)
                description += f"**Suggested**: `{suggested_name}`\n"
                
                suggestion = AgentSuggestion(
                    agent_type=self.agent_type,
                    suggestion_type='naming_convention',
                    title=f"Naming: Use snake_case for {func.name}",
                    description=description,
                    line_number=func.line_start,
                    severity='medium',
                    confidence=0.9,
                    rationale="PEP 8 naming convention"
                )
                suggestions.append(suggestion)
        
        return suggestions
    
    def _check_documentation_requirements(
        self,
        file_analysis: FileAnalysis
    ) -> List[AgentSuggestion]:
        """Check if functions meet documentation requirements."""
        suggestions = []
        doc_rules = self.rules_config.get('documentation', {})
        required_complexity = 5  # From config
        
        for func in file_analysis.functions:
            # Check if complex function lacks documentation
            if func.complexity > required_complexity and not func.docstring:
                description = f"Function `{func.name}` has high complexity ({func.complexity}) but no docstring.\n\n"
                description += f"**Rule**: {doc_rules.get('required_for', [])[2] if len(doc_rules.get('required_for', [])) > 2 else 'Document complex functions'}\n\n"
                description += f"Add a docstring explaining the function's purpose, parameters, and return value.\n"
                
                suggestion = AgentSuggestion(
                    agent_type=self.agent_type,
                    suggestion_type='missing_documentation',
                    title=f"Add docstring to complex function: {func.name}",
                    description=description,
                    line_number=func.line_start,
                    severity='high',
                    confidence=0.95,
                    rationale=f"Complex function (complexity {func.complexity}) requires documentation"
                )
                suggestions.append(suggestion)
        
        return suggestions
    
    def _check_modern_python(
        self,
        file_analysis: FileAnalysis
    ) -> List[AgentSuggestion]:
        """Check for opportunities to use modern Python features."""
        suggestions = []
        code = file_analysis.source_code
        
        # Check for old-style string formatting
        if '"%s"' in code or '"%d"' in code or '".format(' in code:
            description = "Consider using f-strings for string formatting (Python 3.6+).\n\n"
            description += "**Modern Python**: f-strings are more readable and performant.\n\n"
            description += "**Example**:\n"
            description += "```python\n"
            description += '# Instead of:\nname = "Alice"\nmsg = "Hello, %s!" % name\n\n'
            description += '# Use:\nmsg = f"Hello, {name}!"\n'
            description += "```\n"
            
            suggestion = AgentSuggestion(
                agent_type=self.agent_type,
                suggestion_type='modern_python',
                title="Use f-strings instead of % formatting",
                description=description,
                severity='low',
                confidence=0.8,
                rationale="Modern Python best practice",
                metadata={'auto_fix': True}
            )
            suggestions.append(suggestion)
        
        # Check for List/Dict/Tuple imports (should use lowercase in 3.9+)
        if 'from typing import List' in code or 'from typing import Dict' in code:
            description = "Use built-in collection types for type hints (Python 3.9+).\n\n"
            description += "**Modern Python**: Use `list[int]` instead of `List[int]`\n\n"
            description += "**Example**:\n"
            description += "```python\n"
            description += "# Instead of:\nfrom typing import List, Dict\n"
            description += "def process(items: List[str]) -> Dict[str, int]:\n    ...\n\n"
            description += "# Use:\ndef process(items: list[str]) -> dict[str, int]:\n    ...\n"
            description += "```\n"
            
            suggestion = AgentSuggestion(
                agent_type=self.agent_type,
                suggestion_type='modern_python',
                title="Use built-in types for type hints",
                description=description,
                severity='low',
                confidence=0.85,
                rationale="Python 3.9+ feature",
                metadata={'auto_fix': True}
            )
            suggestions.append(suggestion)
        
        return suggestions
    
    async def _analyze_style_with_llm(
        self,
        file_analysis: FileAnalysis
    ) -> List[AgentSuggestion]:
        """Analyze style using LLM with Jinja2 template."""
        
        # Build prompt using Jinja2 template
        prompt = build_style_check_prompt(
            code=file_analysis.source_code,
            language="python",
            file_name=file_analysis.filename,
            style_guide=self.style_guide
        )
        
        try:
            # Call LLM
            response = await self.call_llm(prompt)
            
            # Parse JSON response
            suggestions = self._parse_style_response(response)
            
            return suggestions
        
        except Exception as e:
            logger.error(f"Failed to analyze style: {e}")
            return []
    
    def _parse_style_response(
        self,
        response: str
    ) -> List[AgentSuggestion]:
        """Parse JSON response from LLM."""
        suggestions = []
        
        try:
            # Extract JSON from response
            json_str = self._extract_json(response)
            data = json.loads(json_str)
            
            # Parse style issues
            for issue in data.get('style_issues', []):
                description = f"{issue.get('description', '')}\n\n"
                
                if issue.get('pep_reference'):
                    description += f"**PEP Reference**: {issue['pep_reference']}\n\n"
                
                suggestion = AgentSuggestion(
                    agent_type=self.agent_type,
                    suggestion_type='style',
                    title=f"Style: {issue.get('type', 'Issue').replace('_', ' ').title()}",
                    description=description,
                    line_number=issue.get('line'),
                    severity=issue.get('severity', 'low'),
                    confidence=0.75,
                    rationale=f"Style guide: {self.style_guide}"
                )
                suggestions.append(suggestion)
            
            # Parse style suggestions (fixes)
            for sugg in data.get('style_suggestions', []):
                description = f"{sugg.get('reason', '')}\n\n"
                
                if sugg.get('original_code') and sugg.get('suggested_code'):
                    description += f"**Current**:\n```python\n{sugg['original_code']}\n```\n\n"
                    description += f"**Suggested**:\n```python\n{sugg['suggested_code']}\n```\n\n"
                
                suggestion = AgentSuggestion(
                    agent_type=self.agent_type,
                    suggestion_type='style_fix',
                    title="Style Improvement",
                    description=description,
                    code_snippet=sugg.get('suggested_code'),
                    line_number=sugg.get('line'),
                    severity='low',
                    confidence=0.8,
                    rationale=sugg.get('reason', '')
                )
                suggestions.append(suggestion)
        
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            # Create a general suggestion with the full response
            if response.strip():
                suggestion = AgentSuggestion(
                    agent_type=self.agent_type,
                    suggestion_type='style',
                    title="Code Style Improvements",
                    description=response.strip(),
                    severity='low',
                    confidence=0.6,
                    rationale=f"{self.style_guide} compliance"
                )
                suggestions.append(suggestion)
        
        return suggestions
    
    def _generate_auto_fixes(
        self,
        file_analysis: FileAnalysis,
        existing_suggestions: List[AgentSuggestion]
    ) -> List[AgentSuggestion]:
        """
        Generate auto-fix suggestions for simple style issues.
        
        Args:
            file_analysis: File analysis
            existing_suggestions: Existing suggestions to enhance
        
        Returns:
            Additional auto-fix suggestions
        """
        auto_fix_suggestions = []
        code = file_analysis.source_code
        lines = code.split('\n')
        
        # Check for trailing whitespace
        for i, line in enumerate(lines, 1):
            if line.endswith(' ') or line.endswith('\t'):
                fixed_line = line.rstrip()
                
                description = "Remove trailing whitespace.\n\n"
                description += f"**Current** (line {i}):\n```python\n{repr(line)}\n```\n\n"
                description += f"**Fixed**:\n```python\n{repr(fixed_line)}\n```\n\n"
                description += "**Auto-fix available**: This can be automatically corrected.\n"
                
                suggestion = AgentSuggestion(
                    agent_type=self.agent_type,
                    suggestion_type='auto_fix',
                    title=f"Remove trailing whitespace (line {i})",
                    description=description,
                    code_snippet=fixed_line,
                    line_number=i,
                    severity='low',
                    confidence=1.0,
                    rationale="PEP 8: No trailing whitespace",
                    metadata={
                        'auto_fix': True,
                        'fix_type': 'trailing_whitespace',
                        'original': line,
                        'fixed': fixed_line
                    }
                )
                auto_fix_suggestions.append(suggestion)
        
        # Limit to top 5 auto-fixes to avoid spam
        return auto_fix_suggestions[:5]
    
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
    
    # Helper methods for naming checks
    
    def _is_snake_case(self, name: str) -> bool:
        """Check if name is in snake_case."""
        return name.islower() and '_' in name or name.islower()
    
    def _to_snake_case(self, name: str) -> str:
        """Convert name to snake_case."""
        import re
        # Insert underscores before uppercase letters
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()