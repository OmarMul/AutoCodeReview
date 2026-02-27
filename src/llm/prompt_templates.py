"""
Prompt templates for all specialized agents using Jinja2.
Enhanced version of Task 5.3 prompts with FileAnalysis integration.
"""

from jinja2 import Environment, BaseLoader

env = Environment(loader=BaseLoader(), trim_blocks=True, lstrip_blocks=True)


def render_template(template_str: str, **kwargs) -> str:
    """Render Jinja2 template with provided context."""
    template = env.from_string(template_str)
    return template.render(**kwargs)


# ============================================================================
# CODE ANALYZER AGENT PROMPTS
# ============================================================================

CODE_ANALYZER_SYSTEM_PROMPT = """You are a senior software engineer with extensive experience in conducting comprehensive code reviews across diverse codebases and programming languages.

Your expertise includes:
- Code structure and architectural patterns
- Design patterns and anti-patterns
- Code complexity analysis and refactoring
- Maintainability and readability assessment

Always provide specific, actionable suggestions with code examples."""

CODE_ANALYZER_TEMPLATE = """
Analyze this {{ language }} code for quality issues, focusing on functions with high complexity.

**File**: {{ file_name }}
**Metrics**:
- Total Functions: {{ total_functions }}
- Average Complexity: {{ avg_complexity }}
- Max Complexity: {{ max_complexity }}
- Maintainability Index: {{ maintainability_index }}

**Functions to Review**:
{% for func in functions %}
- **{{ func.name }}** (Lines {{ func.line_start }}-{{ func.line_end }})
  - Complexity: {{ func.complexity }} (Rank: {{ func.rank }})
  - Documented: {{ "Yes" if func.docstring else "No" }}
  {% if func.is_complex %}- ⚠️ HIGH COMPLEXITY{% endif %}
{% endfor %}

**Code**:
```{{ language }}
{{ code }}
```

Please structure your review to include:

1. **Code Structure**: Assess modularity, organization, and adherence to best architectural practices.
2. **Design Patterns**: Identify appropriate or misapplied patterns and their impact on flexibility and scalability.
3. **Readability**: Evaluate clarity, naming conventions, and code documentation.
4. **Maintainability**: Analyze ease of updates, testing, and integration within the existing system.
5. **Anti-patterns**: Detect common pitfalls or suboptimal implementations that could hinder performance or maintainability.

Return your findings strictly in the following JSON format:

{
  "issues": [
    {
      "type": "complexity | readability | design | architecture",
      "function": "function_name",
      "line": int,
      "description": "Detailed issue description",
      "severity": "low | medium | high | critical"
    }
  ],
  "suggestions": [
    {
      "function": "function_name",
      "line": int,
      "title": "Brief suggestion title",
      "original_code": "Code snippet with issue",
      "suggested_code": "Improved code snippet",
      "reason": "Detailed explanation of improvement",
      "impact": "Expected benefit (e.g., reduces complexity from 15 to 8)"
    }
  ],
  "summary": "Overall assessment of code quality"
}
"""


# ============================================================================
# SECURITY AGENT PROMPTS
# ============================================================================

SECURITY_AGENT_SYSTEM_PROMPT = """You are a seasoned cybersecurity professional with extensive experience in secure code review and vulnerability assessment.

Your expertise includes:
- OWASP Top 10 vulnerabilities
- Common Weakness Enumeration (CWE)
- Threat modeling and exploit scenarios
- Secure coding practices

Always explain attack vectors and provide secure code replacements."""

SECURITY_ANALYZER_TEMPLATE = """
Analyze this {{ language }} code for security vulnerabilities.

**File**: {{ file_name }}

**Security Issues Found by Bandit**:
{% if security_issues %}
{% for issue in security_issues %}
- **{{ issue.test_name }}** ({{ issue.test_id }})
  - Line: {{ issue.line_number }}
  - Severity: {{ issue.severity }}
  - Confidence: {{ issue.confidence }}
  - Message: {{ issue.message }}
  - Code: `{{ issue.code }}`
{% endfor %}
{% else %}
No issues found by automated scanner. Perform general security review.
{% endif %}

**Code**:
```{{ language }}
{{ code }}
```

Please conduct a thorough security analysis including:

1. **SQL Injection**: Unsafe query construction and user input handling
2. **XSS (Cross-Site Scripting)**: Improper input sanitization and output encoding
3. **Insecure Deserialization**: Patterns that could lead to RCE or data tampering
4. **Hardcoded Secrets**: API keys, passwords, or cryptographic material in code
5. **Unsafe File Operations**: Arbitrary file access or upload vulnerabilities
6. **Authentication Issues**: Improper implementations or bypass mechanisms

For each Bandit finding, provide:
- Detailed explanation of the vulnerability
- Realistic attack scenario
- Impact assessment
- Specific secure code replacement
- Additional defensive measures

Return your findings strictly in the following JSON format:

{
  "security_issues": [
    {
      "type": "sql_injection | xss | deserialization | hardcoded_secret | command_injection | other",
      "function": "function_name",
      "line": int,
      "vulnerability": "Vulnerability name",
      "cwe_id": "CWE-XXX (if applicable)",
      "severity": "critical | high | medium | low",
      "description": "Detailed vulnerability description",
      "attack_vector": "How this can be exploited",
      "impact": "What attacker gains"
    }
  ],
  "security_suggestions": [
    {
      "function": "function_name",
      "line": int,
      "title": "Security fix title",
      "original_code": "Vulnerable code",
      "suggested_code": "Secure replacement code",
      "reason": "Why this is secure",
      "additional_measures": "Defense-in-depth recommendations"
    }
  ]
}
"""


# ============================================================================
# PERFORMANCE AGENT PROMPTS
# ============================================================================

PERFORMANCE_AGENT_SYSTEM_PROMPT = """You are a seasoned performance optimization specialist with extensive expertise in analyzing and improving code efficiency.

Your expertise includes:
- Algorithmic complexity (Big O notation)
- Data structure optimization
- Memory efficiency
- Python performance characteristics

Always quantify performance improvements."""

PERFORMANCE_ANALYZER_TEMPLATE = """
Analyze this {{ language }} code for performance optimization opportunities.

**File**: {{ file_name }}
**Complexity Metrics**:
- Average Complexity: {{ avg_complexity }}
- Max Complexity: {{ max_complexity }}

**Functions to Analyze**:
{% for func in functions %}
- **{{ func.name }}**: Complexity {{ func.complexity }}{% if func.complexity > 15 %} ⚠️ HIGH COMPLEXITY - likely performance bottleneck{% endif %}
{% endfor %}

**Code**:
```{{ language }}
{{ code }}
```

Please conduct a thorough performance analysis focusing on:

1. **Inefficient Loops**: O(n²) or worse that can be optimized
2. **Redundant Computations**: Calculations that can be cached or eliminated
3. **Memory-Intensive Operations**: Large allocations that can be reduced
4. **N+1 Query Patterns**: Database inefficiencies
5. **Blocking I/O**: Synchronous operations that should be async

For each issue, provide:
- Current algorithmic complexity (Big O)
- Bottleneck identification
- Optimized approach with code example
- Expected performance improvement

Return your findings strictly in the following JSON format:

{
  "performance_issues": [
    {
      "type": "algorithm | memory | io | database | other",
      "function": "function_name",
      "line": int,
      "description": "Performance issue description",
      "current_complexity": "O(?)",
      "severity": "critical | high | medium | low"
    }
  ],
  "performance_suggestions": [
    {
      "function": "function_name",
      "line": int,
      "title": "Optimization suggestion",
      "original_code": "Slow code",
      "suggested_code": "Optimized code",
      "current_complexity": "O(n²)",
      "improved_complexity": "O(n)",
      "expected_speedup": "Estimated performance gain",
      "reason": "Detailed explanation"
    }
  ]
}
"""


# ============================================================================
# DOCUMENTATION AGENT PROMPTS
# ============================================================================

DOCUMENTATION_AGENT_SYSTEM_PROMPT = """You are a technical documentation expert specializing in Python docstrings and API documentation.

Your expertise includes:
- Google, NumPy, and Sphinx docstring styles
- PEP 257 docstring conventions
- Type hints and annotations
- Clear, concise documentation

Always follow best practices for documentation."""

DOCUMENTATION_TEMPLATE = """
Generate comprehensive documentation for this {{ language }} code.

**File**: {{ file_name }}

**Functions Needing Documentation**:
{% for func in functions %}
- **{{ func.name }}** (Lines {{ func.line_start }}-{{ func.line_end }})
  - Arguments: {{ func.args|join(', ') if func.args else 'none' }}
  - Complexity: {{ func.complexity }}
  - Currently Documented: {{ "Yes" if func.docstring else "No ❌" }}
{% endfor %}

**Code**:
```{{ language }}
{{ code }}
```

{% if past_findings %}
**Findings from Other Agents**:
{{ past_findings }}

Please reference these findings in the documentation where relevant.
{% endif %}

Generate professional documentation including:
1. Module-level docstring
2. Function docstrings (Google style)
3. Parameter explanations with types
4. Return value descriptions
5. Exception documentation
6. Usage examples for complex functions

Return your findings strictly in the following JSON format:

{
  "documentation": [
    {
      "type": "module | function | class",
      "name": "function_name",
      "line": int,
      "docstring": "Complete docstring following Google style",
      "includes_example": true/false
    }
  ],
  "summary": "Overview of documentation quality"
}
"""


# ============================================================================
# TEST AGENT PROMPTS
# ============================================================================

TEST_AGENT_SYSTEM_PROMPT = """You are a QA engineer and test-driven development expert specializing in Python testing with pytest.

Your expertise includes:
- Unit testing and test coverage
- Edge cases and boundary conditions
- Mocking and fixtures
- Test-driven development

Always provide runnable pytest test code."""

TEST_CASE_TEMPLATE = """
Suggest comprehensive test cases for this {{ language }} code.

**File**: {{ file_name }}

**Functions to Test**:
{% for func in functions %}
- **{{ func.name }}** (Lines {{ func.line_start }}-{{ func.line_end }})
  - Arguments: {{ func.args|join(', ') if func.args else 'none' }}
  - Complexity: {{ func.complexity }}{% if func.complexity > 10 %} - Complex function needs extensive testing{% endif %}
  - Currently Documented: {{ "Yes" if func.docstring else "No" }}
{% endfor %}

**Code**:
```{{ language }}
{{ code }}
```

For each function, suggest:
1. **Normal Cases**: Expected behavior with valid inputs
2. **Edge Cases**: Empty inputs, None, boundaries, zero, negative values
3. **Failure Scenarios**: Invalid inputs, exceptions, error conditions
4. **Integration Tests**: Interactions with other components (if applicable)

Prioritize functions with:
- High complexity ({{ max_complexity }} max in this file)
- No existing documentation (harder to test)
- Security issues (need security-focused tests)

Return your findings strictly in the following JSON format:

{
  "test_cases": [
    {
      "function": "function_name",
      "test_name": "test_function_name_scenario",
      "description": "What this test verifies",
      "test_type": "normal | edge | error | integration",
      "input": "Test input",
      "expected_output": "Expected result",
      "pytest_code": "Complete runnable pytest test code"
    }
  ]
}
"""


# ============================================================================
# STYLE AGENT PROMPTS
# ============================================================================

STYLE_AGENT_SYSTEM_PROMPT = """You are a Python code style expert enforcing PEP 8 and modern Python best practices.

Your expertise includes:
- PEP 8 style guide
- PEP 257 docstring conventions
- Modern Python idioms (3.10+)
- Code formatting standards

Always reference specific PEP sections."""

STYLE_CHECK_TEMPLATE = """
Check this {{ language }} code for style issues following {{ style_guide }}.

**File**: {{ file_name }}

**Code**:
```{{ language }}
{{ code }}
```

Check for:
1. **Naming Conventions**: snake_case for functions/variables, PascalCase for classes, UPPER_CASE for constants
2. **Indentation**: 4 spaces (no tabs)
3. **Line Length**: Max 88 characters (Black) or 79 (PEP 8)
4. **Imports**: Grouped (stdlib, third-party, local) and sorted
5. **Whitespace**: 2 blank lines between top-level, 1 between methods
6. **Modern Python**: f-strings, type hints, dataclasses, etc.

Return your findings strictly in the following JSON format:

{
  "style_issues": [
    {
      "type": "naming | formatting | imports | whitespace | modern_python",
      "line": int,
      "description": "Style issue description",
      "pep_reference": "PEP 8 section (if applicable)",
      "severity": "low | medium"
    }
  ],
  "style_suggestions": [
    {
      "line": int,
      "original_code": "Non-compliant code",
      "suggested_code": "PEP 8 compliant code",
      "reason": "Why this improves readability"
    }
  ]
}
"""


# ============================================================================
# BUILDER FUNCTIONS
# ============================================================================

def build_code_analysis_prompt(
    code: str,
    language: str,
    file_name: str,
    total_functions: int,
    avg_complexity: float,
    max_complexity: int,
    maintainability_index: float,
    functions: list
) -> str:
    """Build code analysis prompt with metrics."""
    return render_template(
        CODE_ANALYZER_TEMPLATE,
        code=code,
        language=language,
        file_name=file_name,
        total_functions=total_functions,
        avg_complexity=avg_complexity,
        max_complexity=max_complexity,
        maintainability_index=maintainability_index,
        functions=functions
    )


def build_security_analysis_prompt(
    code: str,
    language: str,
    file_name: str,
    security_issues: list
) -> str:
    """Build security analysis prompt with Bandit findings."""
    return render_template(
        SECURITY_ANALYZER_TEMPLATE,
        code=code,
        language=language,
        file_name=file_name,
        security_issues=security_issues
    )


def build_performance_analysis_prompt(
    code: str,
    language: str,
    file_name: str,
    avg_complexity: float,
    max_complexity: int,
    functions: list
) -> str:
    """Build performance analysis prompt."""
    return render_template(
        PERFORMANCE_ANALYZER_TEMPLATE,
        code=code,
        language=language,
        file_name=file_name,
        avg_complexity=avg_complexity,
        max_complexity=max_complexity,
        functions=functions
    )


def build_documentation_prompt(
    code: str,
    language: str,
    file_name: str,
    functions: list,
    past_findings: str = ""
) -> str:
    """Build documentation prompt."""
    return render_template(
        DOCUMENTATION_TEMPLATE,
        code=code,
        language=language,
        file_name=file_name,
        functions=functions,
        past_findings=past_findings
    )


def build_test_case_prompt(
    code: str,
    language: str,
    file_name: str,
    functions: list,
    max_complexity: int
) -> str:
    """Build test case generation prompt."""
    return render_template(
        TEST_CASE_TEMPLATE,
        code=code,
        language=language,
        file_name=file_name,
        functions=functions,
        max_complexity=max_complexity
    )


def build_style_check_prompt(
    code: str,
    language: str,
    file_name: str,
    style_guide: str = "PEP 8"
) -> str:
    """Build style check prompt."""
    return render_template(
        STYLE_CHECK_TEMPLATE,
        code=code,
        language=language,
        file_name=file_name,
        style_guide=style_guide
    )


# ============================================================================
# SYSTEM PROMPTS
# ============================================================================

def get_code_analyzer_system_prompt() -> str:
    return CODE_ANALYZER_SYSTEM_PROMPT


def get_security_agent_system_prompt() -> str:
    return SECURITY_AGENT_SYSTEM_PROMPT


def get_performance_agent_system_prompt() -> str:
    return PERFORMANCE_AGENT_SYSTEM_PROMPT


def get_documentation_agent_system_prompt() -> str:
    return DOCUMENTATION_AGENT_SYSTEM_PROMPT


def get_test_agent_system_prompt() -> str:
    return TEST_AGENT_SYSTEM_PROMPT


def get_style_agent_system_prompt() -> str:
    return STYLE_AGENT_SYSTEM_PROMPT