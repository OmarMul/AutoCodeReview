"""
Security Agent - Analyzes code for security vulnerabilities.
Uses Jinja2 templates and JSON parsing for structured output.
"""

import json
import logging
from typing import Dict, List, Any, Optional

from src.agents.base_agent import (
    BaseAgent,
    AgentType,
    AgentState,
    AgentSuggestion,
    MessageType
)
from src.analyzers.pipeline import FileAnalysis, FunctionAnalysis
from src.analyzers.security_scanner import SecurityIssue, Severity
from src.llm.groq_client import GroqClient
from src.llm.prompt_templates import (
    get_security_agent_system_prompt,
    build_security_analysis_prompt
)

logger = logging.getLogger(__name__)


class SecurityAgent(BaseAgent):
    """
    Security Vulnerability Analysis Agent.
    
    Responsibilities:
    - Analyze security issues found by Bandit
    - Provide context and explanation for vulnerabilities
    - Generate specific fix recommendations
    - Assess threat severity and impact
    - Check for OWASP Top 10 vulnerabilities
    - Suggest security best practices
    """
    
    def __init__(
        self,
        llm_client: GroqClient,
        model: str = "llama-3.3-70b-versatile",
        max_tokens: int = 2500
    ):
        """Initialize Security Agent."""
        super().__init__(
            agent_type=AgentType.SECURITY,
            llm_client=llm_client,
            model=model,
            max_tokens=max_tokens
        )
        
        logger.info("Initialized SecurityAgent")
    
    def get_system_prompt(self) -> str:
        """Get system prompt for security agent."""
        return get_security_agent_system_prompt()
    
    async def analyze(
        self,
        file_analysis: FileAnalysis,
        context: Optional[Dict[str, Any]] = None
    ) -> AgentState:
        """Analyze security vulnerabilities."""
        logger.info(f"SecurityAgent analyzing {file_analysis.filename}")
        
        # Reset state
        self.reset_state()
        
        try:
            # Check if any security issues found
            if file_analysis.total_security_issues == 0:
                logger.info("No security issues found by Bandit")
                
                # Still do a general security check
                general_suggestions = await self._general_security_check(file_analysis)
                for suggestion in general_suggestions:
                    self.state.add_suggestion(suggestion)
                
                self.state.completed = True
                return self.state
            
            # Analyze with LLM using Jinja2 template
            suggestions = await self._analyze_with_llm(file_analysis)
            for suggestion in suggestions:
                self.state.add_suggestion(suggestion)
            
            # Send summary message
            critical_count = sum(
                1 for s in self.state.suggestions 
                if s.severity == "critical"
            )
            
            self.send_message(
                recipient=None,
                message_type=MessageType.ISSUE if critical_count > 0 else MessageType.ANALYSIS,
                content=f"Found {file_analysis.total_security_issues} security issues "
                        f"({critical_count} critical)",
                metadata={
                    'total_issues': file_analysis.total_security_issues,
                    'critical_issues': critical_count
                },
                priority=2 if critical_count > 0 else 1
            )
            
            self.state.completed = True
            logger.info(
                f"SecurityAgent completed: {len(self.state.suggestions)} suggestions "
                f"({critical_count} critical)"
            )
        
        except Exception as e:
            logger.error(f"SecurityAgent failed: {e}", exc_info=True)
            self.state.error = str(e)
            self.state.completed = False
        
        return self.state
    
    async def _analyze_with_llm(
        self,
        file_analysis: FileAnalysis
    ) -> List[AgentSuggestion]:
        """Analyze security issues using LLM with Jinja2 template."""
        # Prepare security issues data for template
        security_issues_data = []
        
        if file_analysis.security_result:
            for issue in file_analysis.security_result.issues:
                security_issues_data.append({
                    'test_id': issue.test_id,
                    'test_name': issue.test_name,
                    'severity': issue.severity.value,
                    'confidence': issue.confidence.value,
                    'line_number': issue.line_number,
                    'code': issue.code,
                    'message': issue.message,
                    'more_info': issue.more_info
                })
        
        # Build prompt using Jinja2 template
        prompt = build_security_analysis_prompt(
            code=file_analysis.source_code,  # ✅ Use actual code
            language="python",
            file_name=file_analysis.filename,
            security_issues=security_issues_data
        )
        
        try:
            # Call LLM
            response = await self.call_llm(prompt)
            
            # Parse JSON response
            suggestions = self._parse_security_response(response, file_analysis)
            
            return suggestions
        
        except Exception as e:
            logger.error(f"Failed to analyze with LLM: {e}")
            
            # Fallback: Create basic suggestions from Bandit findings
            return self._create_fallback_suggestions(file_analysis)
    
    def _parse_security_response(
        self,
        response: str,
        file_analysis: FileAnalysis
    ) -> List[AgentSuggestion]:
        """Parse JSON response from LLM."""
        suggestions = []
        
        try:
            # Extract JSON from response
            json_str = self._extract_json(response)
            data = json.loads(json_str)
            
            # Parse security issues
            for issue in data.get('security_issues', []):
                # Build comprehensive description
                description = f"**Vulnerability**: {issue.get('vulnerability', 'Security Issue')}\n\n"
                description += f"{issue.get('description', '')}\n\n"
                
                if issue.get('attack_vector'):
                    description += f"**Attack Vector**: {issue['attack_vector']}\n\n"
                
                if issue.get('impact'):
                    description += f"**Impact**: {issue['impact']}\n\n"
                
                if issue.get('cwe_id'):
                    description += f"**CWE**: {issue['cwe_id']}\n\n"
                
                suggestion = AgentSuggestion(
                    agent_type=self.agent_type,
                    suggestion_type='security_fix',
                    title=f"Security: {issue.get('vulnerability', 'Vulnerability')}",
                    description=description,
                    line_number=issue.get('line'),
                    severity=issue.get('severity', 'high'),
                    confidence=0.85,
                    rationale=f"Security vulnerability: {issue.get('type', 'unknown')}"
                )
                suggestions.append(suggestion)
            
            # Parse security suggestions (fixes)
            for sugg in data.get('security_suggestions', []):
                description = f"{sugg.get('reason', '')}\n\n"
                
                if sugg.get('suggested_code'):
                    description += f"**Secure Code**:\n```python\n{sugg['suggested_code']}\n```\n\n"
                
                if sugg.get('additional_measures'):
                    description += f"**Additional Measures**: {sugg['additional_measures']}\n\n"
                
                suggestion = AgentSuggestion(
                    agent_type=self.agent_type,
                    suggestion_type='security_fix',
                    title=sugg.get('title', 'Security Fix'),
                    description=description,
                    code_snippet=sugg.get('suggested_code'),
                    line_number=sugg.get('line'),
                    severity='high',
                    confidence=0.9,
                    rationale=sugg.get('reason', '')
                )
                suggestions.append(suggestion)
        
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse JSON response: {e}, using fallback")
            suggestions = self._create_fallback_suggestions(file_analysis)
        
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
    
    def _create_fallback_suggestions(
        self,
        file_analysis: FileAnalysis
    ) -> List[AgentSuggestion]:
        """Create basic suggestions from Bandit findings when LLM fails."""
        suggestions = []
        
        if not file_analysis.security_result:
            return suggestions
        
        for issue in file_analysis.security_result.issues:
            severity = self._map_bandit_severity(issue.severity)
            
            description = f"**Bandit Detection**: {issue.test_name}\n\n"
            description += f"{issue.message}\n\n"
            description += f"**Vulnerable Code**:\n```python\n{issue.code}\n```\n\n"
            
            if issue.more_info:
                description += f"[More Information]({issue.more_info})"
            
            suggestion = AgentSuggestion(
                agent_type=self.agent_type,
                suggestion_type='security_fix',
                title=f"Security: {issue.test_name.replace('_', ' ').title()}",
                description=description,
                line_number=issue.line_number,
                severity=severity,
                confidence=self._map_bandit_confidence(issue.confidence),
                rationale=f"Bandit {issue.test_id}: {issue.message}"
            )
            suggestions.append(suggestion)
        
        return suggestions
    
    def _map_bandit_severity(self, severity: Severity) -> str:
        """Map Bandit severity to agent severity."""
        mapping = {
            Severity.HIGH: "critical",
            Severity.MEDIUM: "high",
            Severity.LOW: "medium",
            Severity.UNDEFINED: "low"
        }
        return mapping.get(severity, "medium")
    
    def _map_bandit_confidence(self, confidence) -> float:
        """Map Bandit confidence to agent confidence."""
        from src.analyzers.security_scanner import Confidence
        
        mapping = {
            Confidence.HIGH: 0.9,
            Confidence.MEDIUM: 0.7,
            Confidence.LOW: 0.5,
            Confidence.UNDEFINED: 0.3
        }
        return mapping.get(confidence, 0.5)
    
    async def _general_security_check(
        self,
        file_analysis: FileAnalysis
    ) -> List[AgentSuggestion]:
        """Perform general security check when Bandit found nothing."""
        # Only do this for files with functions
        if not file_analysis.functions:
            return []
        
        # Simple check - don't use full template
        prompt = f"""Perform a quick security review of this Python code.

File: {file_analysis.filename}

Code:
```python
{file_analysis.source_code[:1000]}  # First 1000 chars only
```

Check for common security concerns:
1. Input validation
2. Authentication/authorization
3. Data exposure
4. Cryptography

If code looks secure, say so briefly. If concerns exist, provide 1-2 most important recommendations.

Return brief JSON:
{{
  "security_issues": [],
  "security_suggestions": []
}}
"""
        
        try:
            response = await self.call_llm(prompt)
            suggestions = self._parse_security_response(response, file_analysis)
            
            # Only return if actual issues found
            return [s for s in suggestions if s.severity in ['high', 'critical']]
        
        except Exception as e:
            logger.error(f"General security check failed: {e}")
            return []