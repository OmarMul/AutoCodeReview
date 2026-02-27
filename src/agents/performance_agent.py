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
    get_performance_agent_system_prompt,
    build_performance_analysis_prompt
)
from src.utils.logger import get_logger

logger = get_logger(__name__)

class PerformanceAgent(BaseAgent):
    """
    Performance Optimization Analysis Agent.
    
    Responsibilities:
    - Identify performance bottlenecks from complexity metrics
    - Analyze algorithmic complexity (Big O)
    - Suggest more efficient algorithms and data structures
    - Identify unnecessary computations and redundant operations
    - Recommend caching and optimization strategies
    - Consider scalability implications
    """

    def __init__(
        self,
        llm_client: GroqClient,
        model: str = "llama-3.3-70b-versatile",
        max_tokens: int = 2000,
        complexity_threshold: int = 15
    ):
        super().__init__(
            agent_type=AgentType.PERFORMANCE,
            llm_client=llm_client,
            model=model,
            max_tokens=max_tokens
        )    
        self.complexity_threshold = complexity_threshold
        
        logger.info(
            f"Initialized PerformanceAgent "
            f"(complexity_threshold={complexity_threshold})"
        )
    
    def get_system_prompt(self) -> str:
        """Get system prompt for performance agent."""
        return get_performance_agent_system_prompt()


    async def analyze(
        self,
        file_analysis: FileAnalysis,
        context: Optional[Dict[str, Any]] = None #additional context from other agents
    ) -> AgentState:

        logger.info(f"PerformanceAgent analyzing {file_analysis.filename}")

        self.reset_state()

        try:
            performance_candidates = self._identify_performance_candidates(file_analysis)

            if not performance_candidates:
                logger.info("No obvious performance issues detected")
                self.state.completed = True
                return self.state
                
            suggestions = await self._analyze_with_llm(
                file_analysis,
                performance_candidates
            )

            for suggestion in suggestions:
                self.state.add_suggestion(suggestion)
            
            high_priority = sum(
                1 for s in self.state.suggestions
                if s.severity in ['high', 'critical']
            )

            self.send_message(
                recipient=None,
                message_type=MessageType.ANALYSIS,
                content=f"Found {len(self.state.suggestions)} performance optimization opportunities "
                        f"({high_priority} high priority)",
                metadata={
                    'total_suggestions': len(self.state.suggestions),
                    'high_priority': high_priority
                }
            )

            self.state.completed = True
            logger.info(
                f"PerformanceAgent completed: {len(self.state.suggestions)} suggestions"
            )
        except Exception as e:
            logger.error(f"PerformanceAgent failed: {e}", exc_info=True)
            self.state.error = str(e)
            self.state.completed = False
        
        return self.state

    def _identify_performance_candidates(
        self,
        file_analysis: FileAnalysis
    ) -> List[FunctionAnalysis]:

        candidates = []
        for func in file_analysis.functions:
            if func.complexity >= self.complexity_threshold:
                candidates.append(func)
                logger.debug(
                    f"Flagged performance candidate: {func.name} "
                    f"(complexity={func.complexity})"
                )
        return candidates

    async def _analyze_with_llm(
        self,
        file_analysis: FileAnalysis,
        performance_candidates: List[FunctionAnalysis]
    ) -> List[AgentSuggestion]:

        functions_data = []
        for func in performance_candidates:
            functions_data.append({
                'name': func.name,
                'line_start': func.line_start,
                'line_end': func.line_end,
                'complexity': func.complexity,
                'rank': func.complexity_rank,
                'args': func.args,
                'docstring': func.docstring
            })

        prompt = build_performance_analysis_prompt(
            code=file_analysis.source_code,
            language="python",
            file_name=file_analysis.filename,
            avg_complexity=file_analysis.average_complexity,
            max_complexity=file_analysis.max_complexity,
            functions=functions_data
        )

        try:
            #call llm
            response = await self.call_llm(prompt)
            # Parse JSON response
            suggestions = self._parse_performance_response(response)
            
            return suggestions
        
        except Exception as e:
            logger.error(f"Failed to analyze performance: {e}")
            return []
    
    def _parse_performance_response(
        self,
        response: str
    ) -> List[AgentSuggestion]:
        """Parse JSON response from LLM."""
        suggestions = []
        
        try:
            # Extract JSON from response
            json_str = self._extract_json(response)
            data = json.loads(json_str)
            
            # Parse performance issues
            for issue in data.get('performance_issues', []):
                description = f"{issue.get('description', '')}\n\n"
                
                if issue.get('current_complexity'):
                    description += f"**Current Complexity**: {issue['current_complexity']}\n\n"
                
                suggestion = AgentSuggestion(
                    agent_type=self.agent_type,
                    suggestion_type='performance',
                    title=f"Performance: {issue.get('type', 'Optimization').title()}",
                    description=description,
                    line_number=issue.get('line'),
                    severity=issue.get('severity', 'medium'),
                    confidence=0.8,
                    rationale=f"Performance bottleneck: {issue.get('type', 'unknown')}"
                )
                suggestions.append(suggestion)
            
            # Parse performance suggestions
            for sugg in data.get('performance_suggestions', []):
                description = f"{sugg.get('reason', '')}\n\n"
                
                if sugg.get('current_complexity') and sugg.get('improved_complexity'):
                    description += (
                        f"**Complexity Improvement**: "
                        f"{sugg['current_complexity']} → {sugg['improved_complexity']}\n\n"
                    )
                
                if sugg.get('expected_speedup'):
                    description += f"**Expected Speedup**: {sugg['expected_speedup']}\n\n"
                
                if sugg.get('suggested_code'):
                    description += (
                        f"**Optimized Code**:\n```python\n{sugg['suggested_code']}\n```\n\n"
                    )
                
                suggestion = AgentSuggestion(
                    agent_type=self.agent_type,
                    suggestion_type='optimization',
                    title=sugg.get('title', 'Performance Optimization'),
                    description=description,
                    code_snippet=sugg.get('suggested_code'),
                    line_number=sugg.get('line'),
                    severity='high' if 'critical' in sugg.get('title', '').lower() else 'medium',
                    confidence=0.85,
                    rationale=sugg.get('reason', '')
                )
                suggestions.append(suggestion)
        
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            # Create a general suggestion with the full response
            if response.strip():
                suggestion = AgentSuggestion(
                    agent_type=self.agent_type,
                    suggestion_type='performance',
                    title="Performance Optimization Opportunities",
                    description=response.strip(),
                    severity='medium',
                    confidence=0.6,
                    rationale="General performance analysis"
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

    
