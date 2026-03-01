from typing import Dict, List, Any, Optional, Annotated, TypedDict
import operator

from src.agents.base_agent import AgentState, AgentSuggestion, AgentMessage
from src.analyzers.pipeline import FileAnalysis


class AgentNodeState(TypedDict, total=False):
    """Result from a single agent node."""
    completed: bool
    suggestions: List[AgentSuggestion]
    messages: List[AgentMessage]
    error: Optional[str]


class WorkflowState(TypedDict):
    """
    Main state for the LangGraph Orchestrator.
    We use Annotated with operator.add or custom reducers for fields that
    need to aggregate across parallel nodes.
    """
    # Inputs
    file_analysis: FileAnalysis
    
    # Configuration / Context
    context: Dict[str, Any]
    
    # We use a simple dictionary to hold individual agent states for visibility/debugging
    # Key is agent type string, Value is AgentNodeState dict
    agent_results: Annotated[Dict[str, AgentNodeState], lambda x, y: {**x, **y}]

    # Aggregated outputs from all parallel nodes
    all_suggestions: Annotated[List[AgentSuggestion], operator.add]
    all_messages: Annotated[List[AgentMessage], operator.add]
    
    # Track which agents failed or succeeded
    completed_agents: Annotated[List[str], operator.add]
    failed_agents: Annotated[List[str], operator.add]
    errors: Annotated[List[str], operator.add]
    
    # Final output status after aggregator
    status: str
    report_markdown: str
