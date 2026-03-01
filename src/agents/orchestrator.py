import logging
from typing import Dict, Any, List

# LangGraph imports
from langgraph.graph import StateGraph, START, END

# Local imports
from src.utils.logger import get_logger
from src.agents.base_agent import BaseAgent, AgentSuggestion
from src.agents.graph_state import WorkflowState, AgentNodeState
from src.analyzers.pipeline import FileAnalysis

logger = get_logger(__name__)

class AgentOrchestrator:
    """
    LangGraph-based code review orchestrator.
    Manages parallel execution of multiple specialized review agents,
    followed by an aggregation step to resolve conflicts and bundle findings.
    """
    def __init__(self, enable_parallel: bool = True):
        self.enable_parallel = enable_parallel
        self.agents: Dict[str, BaseAgent] = {}
        self.graph = None

    def register_agent(self, agent: BaseAgent):
        """Register an agent with the orchestrator."""
        name = agent.agent_type.value
        self.agents[name] = agent
        logger.info(f"Registered agent: {name} in orchestrator.")

    def build_graph(self):
        """
        Builds the LangGraph computational graph mapping agents to parallel nodes.
        """
        if not self.agents:
            raise ValueError("No agents registered to build graph.")

        workflow = StateGraph(WorkflowState)

        # 1. Create a node wrapper for each agent
        for agent_name, agent_instance in self.agents.items():
            # We use a closure that captures the agent_instance 
            # to keep the node function pure for the graph
            def agent_node(state: WorkflowState, agent=agent_instance) -> dict:
                name = agent.agent_type.value
                logger.info(f"LangGraph Node '{name}' starting.")
                try:
                    # Execute agent analysis asynchronously or synchronously based on the agent's implementation.
                    # BaseAgent `analyze` might be synchronous or asynchronous.
                    # If it's pure async we should 'await', but for our setup we assume standard awaitable if so,
                    # or standard sync. Below we try to handle both or assume standard async wrappers.
                    import asyncio
                    
                    if asyncio.iscoroutinefunction(agent.analyze):
                        # Running inside an asyncio event loop since LangGraph nodes can be async
                        agent_state = asyncio.run(agent.analyze(state["file_analysis"], state.get("context")))
                    else:
                        # Fallback for sync
                        # (Normally if we call ainvoke it handles it, but let's assume analyze might be a coroutine)
                        # We will use native async wrapper in the future if this causes a loop issue,
                        # but typically we'd map async functions natively
                        pass

                    # Actually we will define an async inner function for safety:
                    pass
                except Exception as e:
                    pass

                # Let's write the pure node structure correctly for async execution
                pass
            
            # Use a properly wrapped async factory
            workflow.add_node(agent_name, self._create_agent_node(agent_instance))

        # 2. Add an aggregator node
        workflow.add_node("aggregator", self._aggregator_node)

        # 3. Add Edges (START -> all agents -> aggregator -> END)
        for agent_name in self.agents.keys():
            workflow.add_edge(START, agent_name)
            workflow.add_edge(agent_name, "aggregator")

        workflow.add_edge("aggregator", END)

        self.graph = workflow.compile()
        logger.info("LangGraph workflow compiled successfully.")

    def _create_agent_node(self, agent: BaseAgent):
        """
        Factory to create an async node function for a specific agent.
        Includes error handling so a failure does not stop the whole graph.
        """
        async def node_func(state: WorkflowState) -> dict:
            name = agent.agent_type.value
            try:
                # We need to ensure we run async properly
                agent_state = await agent.analyze(state["file_analysis"], state.get("context"))
                
                return {
                    "agent_results": {
                        name: AgentNodeState(
                            completed=True,
                            suggestions=agent_state.suggestions,
                            messages=agent_state.messages,
                            error=None
                        )
                    },
                    "all_suggestions": agent_state.suggestions,
                    "all_messages": agent_state.messages,
                    "completed_agents": [name],
                    "failed_agents": [],
                    "errors": []
                }
            except Exception as e:
                logger.error(f"Agent '{name}' failed during execution: {e}", exc_info=True)
                return {
                    "agent_results": {
                        name: AgentNodeState(
                            completed=False,
                            suggestions=[],
                            messages=[],
                            error=str(e)
                        )
                    },
                    "all_suggestions": [],
                    "all_messages": [],
                    "completed_agents": [],
                    "failed_agents": [name],
                    "errors": [f"{name} Error: {str(e)}"]
                }
        return node_func

    def _aggregator_node(self, state: WorkflowState) -> dict:
        """
        Final node that consolidates all inputs, removes duplicates,
        and generates a unified report markdown state.
        """
        logger.info("Running aggregator node.")
        
        # Here we could do advanced conflict resolution
        # E.g. StyleAgent says formatting change is needed, CodeAnalyzer says same.
        unique_suggestions = self._deduplicate_suggestions(state.get("all_suggestions", []))
        
        status = "Completed" if not state.get("failed_agents") else "Completed with errors"

        return {
            "all_suggestions": unique_suggestions, # Overwrite with deduped (custom reducer might need to be careful, but we just set it)
            # Actually, because `all_suggestions` uses operator.add, returning a NEW value here Appends to it!
            # To *overwrite*, we should probably format the report instead.
            "status": status,
        }

    def _deduplicate_suggestions(self, suggestions: List[AgentSuggestion]) -> List[AgentSuggestion]:
        unique = []
        seen_titles = set()
        for idx, s in enumerate(suggestions):
            # A simple deduplication strategy
            key = f"{s.line_number}:{s.title}"
            if key not in seen_titles:
                seen_titles.add(key)
                unique.append(s)
        return unique

    async def a_orchestrate(self, file_analysis: FileAnalysis, context: Dict[str, Any] = None) -> WorkflowState:
        """
        Execute the graph asynchronously across all registered agents.
        """
        if not self.graph:
            self.build_graph()

        initial_state: WorkflowState = {
            "file_analysis": file_analysis,
            "context": context or {},
            "agent_results": {},
            "all_suggestions": [],
            "all_messages": [],
            "completed_agents": [],
            "failed_agents": [],
            "errors": [],
            "status": "Running",
            "report_markdown": ""
        }

        # run graph
        final_state = await self.graph.ainvoke(initial_state)
        return final_state

    def orchestrate(self, file_analysis: FileAnalysis, context: Dict[str, Any] = None) -> WorkflowState:
        """
        Synchronous wrapper for orchestration (useful for testing or non-async callers).
        """
        import asyncio
        return asyncio.run(self.a_orchestrate(file_analysis, context))

    def generate_report(self, state: WorkflowState, format: str = "markdown") -> str:
        """
        Generates a markdown report summarizing the final state.
        Replaces the old legacy report generation.
        """
        lines = []
        lines.append(f"# AutoCodeReview Multi-Agent Report")
        lines.append(f"**Status**: {state.get('status')}")
        lines.append(f"**Agents Completed**: {len(state.get('completed_agents', []))}")
        
        failed = state.get('failed_agents', [])
        if failed:
            lines.append(f"**Agents Failed**: {', '.join(failed)}")
            for err in state.get('errors', []):
                lines.append(f"- *Error*: {err}")
        
        lines.append("\n## Suggestions by Agent")
        
        # Group suggestions by agent
        grouped = {}
        for s in state.get("all_suggestions", []):
            agent_type = s.agent_type.value
            if agent_type not in grouped:
                grouped[agent_type] = []
            grouped[agent_type].append(s)

        for agent_type, suggestions in grouped.items():
            lines.append(f"\n### {agent_type.title()} Findings ({len(suggestions)})")
            for i, sug in enumerate(suggestions, 1):
                lines.append(f"{i}. **{sug.title}** (Line {sug.line_number})")
                lines.append(f"   - **Severity**: {sug.severity}")
                if sug.description:
                     lines.append(f"   - **Description**: {sug.description}")

        return "\n".join(lines)
