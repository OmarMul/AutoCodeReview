"""
Test PerformanceAgent and DocumentationAgent.
"""

import asyncio
from src.llm.groq_client import GroqClient
from src.agents.performance_agent import PerformanceAgent
from src.agents.documentation_agent import DocumentationAgent
from src.agents.orchestrator import AgentOrchestrator
from src.analyzers.pipeline import AnalysisPipeline

# Sample code with performance and documentation issues
SAMPLE_CODE = """
def find_duplicates(items):
    # No docstring - documentation issue
    # O(n²) complexity - performance issue
    duplicates = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if items[i] == items[j] and items[i] not in duplicates:
                duplicates.append(items[i])
    return duplicates

def process_large_dataset(data):
    # Minimal docstring
    '''Process data.'''
    # Multiple performance issues
    result = []
    for item in data:
        # Nested loops - O(n²)
        for other in data:
            if item['id'] != other['id']:
                # String concatenation in loop
                combined = ""
                for char in item['name']:
                    combined += char
                result.append(combined)
    return result

def calculate_statistics(numbers):
    # No docstring, complex function
    total = sum(numbers)
    mean = total / len(numbers)
    
    # Inefficient: recalculating sum
    variance = sum((x - mean) ** 2 for x in numbers) / len(numbers)
    
    # Inefficient: multiple passes
    sorted_nums = sorted(numbers)
    median = sorted_nums[len(sorted_nums) // 2]
    
    return {'mean': mean, 'variance': variance, 'median': median}

def well_documented_function(x: int, y: int) -> int:
    '''
    Add two numbers together.
    
    Args:
        x: First number
        y: Second number
    
    Returns:
        Sum of x and y
    
    Example:
        >>> well_documented_function(2, 3)
        5
    '''
    return x + y
"""


async def main():
    print("=" * 80)
    print("DAY 15: PERFORMANCE & DOCUMENTATION AGENTS TEST")
    print("=" * 80)
    print()
    
    # Step 1: Run analysis pipeline
    print("Step 1: Running Analysis Pipeline...")
    print("-" * 80)
    pipeline = AnalysisPipeline()
    file_analysis = pipeline.analyze_file(SAMPLE_CODE, "performance_doc_test.py")
    
    print(f"✓ Analysis Complete")
    print(f"  - Functions: {file_analysis.total_functions}")
    print(f"  - Avg Complexity: {file_analysis.average_complexity:.1f}")
    print(f"  - Max Complexity: {file_analysis.max_complexity}")
    print()
    
    # Step 2: Initialize LLM client
    print("Step 2: Initializing LLM Client...")
    print("-" * 80)
    llm_client = GroqClient()
    print("✓ GroqClient ready")
    print()
    
    # Step 3: Test PerformanceAgent
    print("Step 3: Testing PerformanceAgent...")
    print("-" * 80)
    performance_agent = PerformanceAgent(llm_client, complexity_threshold=5)
    
    print("Analyzing performance...")
    performance_state = await performance_agent.analyze(file_analysis)
    
    print(f"✓ PerformanceAgent completed")
    print(f"  - Status: {'Success' if performance_state.completed else 'Failed'}")
    print(f"  - Suggestions: {len(performance_state.suggestions)}")
    print(f"  - Messages: {len(performance_state.messages)}")
    
    if performance_state.suggestions:
        print("\nPerformance Optimization Suggestions:")
        for i, suggestion in enumerate(performance_state.suggestions[:3], 1):
            print(f"\n  {i}. {suggestion.title}")
            print(f"     Line: {suggestion.line_number}")
            print(f"     Severity: {suggestion.severity}")
            print(f"     {suggestion.description[:200]}...")
    print()
    
    # Step 4: Test DocumentationAgent
    print("Step 4: Testing DocumentationAgent...")
    print("-" * 80)
    doc_agent = DocumentationAgent(llm_client)
    
    print("Generating documentation...")
    doc_state = await doc_agent.analyze(file_analysis)
    
    print(f"✓ DocumentationAgent completed")
    print(f"  - Status: {'Success' if doc_state.completed else 'Failed'}")
    print(f"  - Suggestions: {len(doc_state.suggestions)}")
    print(f"  - Messages: {len(doc_state.messages)}")
    
    if doc_state.suggestions:
        print("\nDocumentation Suggestions:")
        for i, suggestion in enumerate(doc_state.suggestions[:3], 1):
            print(f"\n  {i}. {suggestion.title}")
            print(f"     Line: {suggestion.line_number}")
            print(f"     {suggestion.description[:300]}...")
    print()
    
    # Step 5: Test with Orchestrator
    print("Step 5: Testing with Orchestrator (All 4 Agents)...")
    print("-" * 80)
    
    from src.agents.code_analyzer_agent import CodeAnalyzerAgent
    from src.agents.security_agent import SecurityAgent
    
    orchestrator = AgentOrchestrator(llm_client, enable_parallel=True)
    orchestrator.register_agent(CodeAnalyzerAgent(llm_client))
    orchestrator.register_agent(SecurityAgent(llm_client))
    orchestrator.register_agent(performance_agent)
    orchestrator.register_agent(doc_agent)
    
    print("Running all 4 agents in parallel...")
    workflow_state = orchestrator.orchestrate(file_analysis)
    
    print(f"✓ Orchestration Complete")
    print(f"  - Completed Agents: {len(workflow_state.completed_agents)}")
    print(f"  - Failed Agents: {len(workflow_state.failed_agents)}")
    print(f"  - Total Suggestions: {len(workflow_state.all_suggestions)}")
    print()
    
    # Step 6: Generate report
    print("Step 6: Generating Combined Report...")
    print("=" * 80)
    report = orchestrator.generate_report(workflow_state, format="markdown")
    print(report[:2000])  # Print first 2000 chars
    print("\n[... report continues ...]")
    print()
    
    print("=" * 80)
    print("DAY 15 TESTING COMPLETE!")
    print("=" * 80)
    print()
    print(f"Summary:")
    print(f"  - 4 agents successfully tested")
    print(f"  - Total suggestions: {len(workflow_state.all_suggestions)}")
    print(f"  - Code Analyzer: {sum(1 for s in workflow_state.all_suggestions if s.agent_type.value == 'code_analyzer')}")
    print(f"  - Security: {sum(1 for s in workflow_state.all_suggestions if s.agent_type.value == 'security')}")
    print(f"  - Performance: {sum(1 for s in workflow_state.all_suggestions if s.agent_type.value == 'performance')}")
    print(f"  - Documentation: {sum(1 for s in workflow_state.all_suggestions if s.agent_type.value == 'documentation')}")


if __name__ == "__main__":
    asyncio.run(main())
    