import asyncio
from src.llm.groq_client import GroqClient
from src.llm.prompt_templates import build_documentation_prompt

past_findings = """
```json
{
  "issues": [
    {
      "type": "style",
      "file": "example.py",
      "line": 1,
      "description": "Lack of proper function documentation and comments",
      "severity": "low"
    },
    {
      "type": "style",
      "file": "example.py",
      "line": 1,
      "description": "Inconsistent naming conventions, the function name 'add' is not following PEP 8 standards for function naming",
      "severity": "low"
    },
    {
      "type": "security",
      "file": "example.py",
      "line": 1,
      "description": "Potential risk of SQL or command injection if the input is not validated and sanitized",
      "severity": "medium"
    },
    {
      "type": "style",
      "file": "example.py",
      "line": 1,
      "description": "Function is not following the principle of least surprise, it does not handle potential exceptions or errors",
      "severity": "low"
    },
    {
      "type": "other",
      "file": "example.py",
      "line": 1,
      "description": "The code does not follow best practices, a more Pythonic way of writing this would be to use a more descriptive name for the function and to include input validation",
      "severity": "low"
    }
  ],
  "suggestions": [
    {
      "file": "example.py",
      "line": 1,
      "original_code": "def add(a,b):return a+b",
      "suggested_code": "def add_numbers(a: int, b: int) -> int:\n    '''Adds two numbers together.\n\n    Args:\n        a (int): The first number to add.\n        b (int): The second number to add.\n\n    Returns:\n        int: The sum of a and b.\n    '''\n    try:\n        return a + b\n    except 
TypeError:\n        raise ValueError('Both inputs must be numbers')",
      "reason": "Improved code readability and adherence to PEP 8 standards, added input validation and error handling"
  ],
  "metrics": {
    "complexity_score": 1.0,
    "coverage_score": 0.0,
    "security_score": 0.5
  },
  "summary": "The provided code lacks proper documentation, does not follow best practices, and has potential security risks. Suggestions are provided to improve code quality, readability, and maintainability."
}
```
Here is my evaluation of the provided code:After conducting an in-depth analysis, I did not find any SQL Injection vulnerabilities, Cross-Site Scripting (XSS) risks, insecure deserialization patterns, hardcoded secrets, insecure file handling mechanisms, or improper authentication logic. This is because the provided code is a simple arithmetic operation and does not involve any user input, database interactions, file operations, or network communications.

However, I do have a few security suggestions to improve the code:


The code can be improved by adding input validation to ensure that the inputs are numbers. Additionally, the function can be made more robust by handling potential exceptions.


Here are my findings in the requested JSON format:
{
  "security_issues": [
    {
      "type": "security",
      "file": "example.py",
      "line": 1,
      "description": "The function does not validate its inputs, which could lead to a TypeError if non-numeric values are passed.",
      "severity": "low"
    }
  ],
  "security_suggestions": [
    {
      "file": "example.py",
      "line": 1,
      "original_code": "def add(a,b):return a+b",
      "suggested_code": "def add(a, b):\n    if not isinstance(a, (int, float)) or not isinstance(b, 
(int, float)):\n        raise TypeError(\"Both inputs must be numbers\")\n    return a + b",
      "reason": "Input validation to prevent potential TypeErrors and improve code robustness."      
    }
  ]
}
"""

prompt = build_documentation_prompt(
    code="def add(a,b):return a+b",
    language="python",
    file_name="example.py",
    past_findings=past_findings
)

async def test():
    client = GroqClient()

    response = await client.generate(
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    print(response["choices"][0]["message"]["content"])

asyncio.run(test())
