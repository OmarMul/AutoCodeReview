import asyncio
import pytest
from src.llm.groq_client import GroqClient
from src.agents.orchestrator import AgentOrchestrator
from src.analyzers.pipeline import AnalysisPipeline
from src.agents.code_analyzer_agent import CodeAnalyzerAgent
from src.agents.security_agent import SecurityAgent
from src.agents.performance_agent import PerformanceAgent
from src.agents.documentation_agent import DocumentationAgent
from src.agents.style_agent import StyleAgent
from src.agents.test_agent import TestAgent


SAMPLE_CODE = """
def process_data(user_input):
    # Missing docstring and bad var names
    data = eval(user_input)  # Security vulnerability
    
    lst = []
    # Performance issue O(N^2)
    for i in data:
        for j in data:
            if i == j:
                lst.append(i)
                
    return lst
"""


@pytest.mark.asyncio
async def test_langgraph_orchestrator_e2e():
    print("\n[TEST] Starting LangGraph end-to-end test with real LLMs...")

    # 1. Pipeline Analysis
    pipeline = AnalysisPipeline()
    file_analysis = pipeline.analyze_file(SAMPLE_CODE, "sample.py")
    assert file_analysis.total_functions > 0, "Pipeline should find the function"

    # 2. Setup Agents
    client = GroqClient()
    orchestrator = AgentOrchestrator()
    
    orchestrator.register_agent(CodeAnalyzerAgent(client))
    orchestrator.register_agent(SecurityAgent(client))
    orchestrator.register_agent(PerformanceAgent(client))
    orchestrator.register_agent(DocumentationAgent(client))
    orchestrator.register_agent(StyleAgent(client))
    orchestrator.register_agent(TestAgent(client))

    # 3. Run Graph
    print(f"[TEST] Invoking Orchestrator with {len(orchestrator.agents)} agents...")
    workflow_state = await orchestrator.a_orchestrate(file_analysis)

    # 4. Verify output
    assert workflow_state["status"].startswith("Completed"), f"Graph status: {workflow_state['status']}"
    
    # Assert at least some agents completed successfully
    assert len(workflow_state["completed_agents"]) > 0, "At least one agent should complete successfully"
    
    # Assert suggestions exist
    print(f"[TEST] Found {len(workflow_state['all_suggestions'])} total deduped suggestions.")
    # Assuming LLM responds with at least 1 suggestion given the terrible code block
    assert len(workflow_state["all_suggestions"]) > 0, "Should generate some suggestions"

    report = orchestrator.generate_report(workflow_state)
    print("\n--- Final Generated Report Preview ---")
    print(report[:1000])

    print("\n--- End of Test ---")

if __name__ == "__main__":
    asyncio.run(test_langgraph_orchestrator_e2e())
