from jinja2 import Environment, BaseLoader

env = Environment(loader=BaseLoader(), trim_blocks=True, lstrip_blocks=True)


def render_template(template_str: str, **kwargs) -> str:
    template = env.from_string(template_str)
    return template.render(**kwargs)

CODE_ANALYSIS_TEMPLATE = """
You are a senior software engineer with extensive experience in conducting comprehensive code reviews across diverse codebases and programming languages. I require your expertise to perform an in-depth analysis of the provided {{ language }} code, focusing on critical aspects that influence code quality and long-term sustainability.

Analyze the following {{ language }} code.

Code:

```{{ language }}
{{ code }}"

Please structure your review to include:

Code Structure: Assess modularity, organization, and adherence to best architectural practices.
Design Patterns: Identify appropriate or misapplied patterns and their impact on flexibility and scalability.
Readability: Evaluate clarity, naming conventions, and code documentation.
Maintainability: Analyze ease of updates, testing, and integration within the existing system.
Anti-patterns: Detect common pitfalls or suboptimal implementations that could hinder performance or maintainability.

Return your findings strictly in the following comprehensive JSON format:

{
  "issues": [
    {
      "type": "bug | performance | security | style | other",
      "file": "{{ file_name }}",
      "line": int,
      "description": "Issue description",
      "severity": "low | medium | high"
    }
  ],
  "suggestions": [
    {
      "file": "{{ file_name }}",
      "line": int,
      "original_code": "Original code",
      "suggested_code": "Suggested code",
      "reason": "Reason for suggestion"
    }
  ],
  "metrics": {
    "complexity_score": float,
    "coverage_score": float,
    "security_score": float,
  },
  "summary": "Summary of the code review"
}
"""

SECURITY_REVIEW_TEMPLATE = """
You are a seasoned cybersecurity professional with extensive experience in secure code review and vulnerability assessment. I request your expertise to conduct an in-depth analysis of the provided source code to identify critical security flaws.

Please ensure your evaluation includes:

Detection of SQL Injection vulnerabilities, focusing on unsafe query construction and user input handling.
Identification of Cross-Site Scripting (XSS) risks, including improper input sanitization and output encoding.
Examination for insecure deserialization patterns that could lead to remote code execution or data tampering.
Discovery of hardcoded secrets such as API keys, passwords, or cryptographic material embedded within the codebase.
Analysis of file handling mechanisms for unsafe operations that could result in arbitrary file access or upload vulnerabilities.
Verification of authentication logic to uncover improper implementations or bypass mechanisms.

Analyze the following {{ language }} code.

Code:

```{{ language }}
{{ code }}"

Return your findings strictly in the following comprehensive JSON format:

{
  "security_issues": [
    {
      "type": "bug | performance | security | style | other",
      "file": "{{ file_name }}",
      "line": int,
      "description": "Issue description",
      "severity": "low | medium | high"
    }
  ],
  "security_suggestions": [
    {
      "file": "{{ file_name }}",
      "line": int,
      "original_code": "Original code",
      "suggested_code": "Suggested code",
      "reason": "Reason for suggestion"
    }
  ]
}
"""

PERFORMANCE_TEMPLATE = """
You are a seasoned performance optimization specialist with extensive expertise in analyzing and improving code efficiency across various programming languages. I request your detailed evaluation of the provided {{ language }} source code to identify potential performance bottlenecks and optimization opportunities.

Please conduct a thorough analysis focusing on the following aspects:

Detect inefficient loops that can be refactored for better time complexity or reduced resource consumption.
Identify redundant computations that may be eliminated or cached to enhance execution speed.
Highlight memory-intensive operations that could be optimized to lower memory footprint and improve scalability.
Spot occurrences of N+1 query patterns that degrade database performance, suggesting batch retrieval or eager loading alternatives.
Examine asynchronous contexts for blocking I/O operations that impede concurrency and propose non-blocking approaches.

Analyze the following {{ language }} code.

Code:

```{{ language }}
{{ code }}"

Return your findings strictly in the following comprehensive JSON format:

{
  "performance_issues": [
    {
      "type": "bug | performance | security | style | other",
      "file": "{{ file_name }}",
      "line": int,
      "description": "Issue description",
      "severity": "low | medium | high"
    }
  ],
  "performance_suggestions": [
    {
      "file": "{{ file_name }}",
      "line": int,
      "original_code": "Original code",
      "suggested_code": "Suggested code",
      "reason": "Reason for suggestion"
    }
  ]
}
"""
DOCUMENTATION_TEMPLATE =""" 
    # Expert Role Assignment
    You are a specialized professional with expertise in creating high-quality content.

    # Task & Purpose
    Create a detailed, comprehensive response based on this request
    You are a senior developer generating professional documentation.

    Generate:
    - Docstrings
    - Function descriptions
    - Parameter explanations
    - Return value explanations
    - Include all the Findings from past Agents {{past_findings}} do it in well structured docx format evert agent has its own section.

    Return JSON:

    {
    "documentation": "Full documentation here"
    }

    Code:

    ```{{ language }}
    {{ code }}"

    # Content Structure
    Organize your response with clear sections, logical flow, and appropriate hierarchy.
    The First Header Should be "Documentation for {{file_name}}".
    
    # Required Elements
    - Include specific, actionable information rather than general statements
    - Provide concrete examples or applications where appropriate
    - Address all key aspects of the request with appropriate depth
    - Incorporate relevant context and background information

    # Style & Approach
    - Use natural, professional language that avoids AI-sounding patterns
    - Maintain a balanced tone that matches the subject matter
    - Employ clear, precise terminology appropriate to the topic
    - Write in active voice with concise, well-structured sentences

    # Quality Standards
    - Ensure factual accuracy and logical consistency throughout
    - Provide sufficient detail to be genuinely useful
    - Maintain appropriate scope - neither too broad nor too narrow
    - Create content that demonstrates domain expertise

    # Output Format
    Present your response in a well-structured format with clear headings, concise paragraphs, and appropriate use of formatting to highlight key points.
"""

TEST_CASE_TEMPLATE = """# Expert Role Assignment
You are a specialized professional with expertise in creating high-quality content.

# Task & Purpose
Create a detailed, comprehensive response based on this request:
You are a QA engineer.

Suggest:
- Edge cases
- Boundary tests
- Failure scenarios
- Unit tests

Return JSON:

{
  "test_cases": [
    {
      "description": "...",
      "input": "...",
      "expected_output": "..."
    }
  ]
}

Code:

```{{ language }}
{{ code }}"

# Content Structure
Organize your response with clear sections, logical flow, and appropriate hierarchy.

# Required Elements
- Include specific, actionable information rather than general statements
- Provide concrete examples or applications where appropriate
- Address all key aspects of the request with appropriate depth
- Incorporate relevant context and background information

# Style & Approach
- Use natural, professional language that avoids AI-sounding patterns
- Maintain a balanced tone that matches the subject matter
- Employ clear, precise terminology appropriate to the topic
- Write in active voice with concise, well-structured sentences

# Quality Standards
- Ensure factual accuracy and logical consistency throughout
- Provide sufficient detail to be genuinely useful
- Maintain appropriate scope - neither too broad nor too narrow
- Create content that demonstrates domain expertise

# Output Format
Present your response in a well-structured format with clear headings, concise paragraphs, and appropriate use of formatting to highlight key points."""

STYLE_CHECK_TEMPLATE = """
You are enforcing {{ style_guide }} coding standards.

Check for:
- Naming conventions
- Indentation
- Line length
- Imports order
- Code formatting

Return JSON:

{
  "style_issues": [
    {
      "file_path": "{{ file_name }}",
      "description": "...",
      "severity": "low | medium"
    }
  ]
}

Code:

```{{ language }}
{{ code }}
"""

def build_code_analysis_prompt(code: str, language: str, file_name: str):
    return render_template(CODE_ANALYSIS_TEMPLATE, code=code, language=language, file_name=file_name)

def build_security_analysis_prompt(code: str, language: str, file_name: str):
    return render_template(SECURITY_REVIEW_TEMPLATE, code=code, language=language, file_name=file_name)

def build_performance_analysis_prompt(code: str, language: str, file_name: str):
    return render_template(PERFORMANCE_TEMPLATE, code=code, language=language, file_name=file_name)

def build_documentation_prompt(code: str, language: str, past_findings: str, file_name:str):
    return render_template(DOCUMENTATION_TEMPLATE, code=code, language=language, past_findings=past_findings, file_name=file_name)

def build_test_case_prompt(code: str, language: str, file_name: str):
    return render_template(TEST_CASE_TEMPLATE, code=code, language=language, file_name=file_name)

def build_style_check_prompt(code: str, language: str, file_name: str, style_guide: str):
    return render_template(STYLE_CHECK_TEMPLATE, code=code, language=language, file_name=file_name, style_guide=style_guide)