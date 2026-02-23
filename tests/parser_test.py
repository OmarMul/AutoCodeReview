"""
Tests for Python parser.
"""

import pytest
from src.parsers.python_parser import PythonParser

class TestPythonParser:
    """Test Python code parsing."""
    
    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return PythonParser()
    
    def test_parse_simple_function(self, parser):
        """Test parsing a simple function."""
        code = """
def hello_world():
    '''Say hello.'''
    print("Hello, World!")
"""
        result = parser.parse(code)
        
        assert len(result.functions) == 1
        assert result.functions[0].name == "hello_world"
        assert result.functions[0].docstring == "Say hello."
        assert result.error is None
    
    def test_parse_function_with_args(self, parser):
        """Test parsing function with arguments."""
        code = """
def add(a, b):
    return a + b
"""
        result = parser.parse(code)
        
        assert len(result.functions) == 1
        func = result.functions[0]
        assert func.name == "add"
        assert func.args == ["a", "b"]
    
    def test_parse_async_function(self, parser):
        """Test parsing async function."""
        code = """
async def fetch_data():
    return await get_data()
"""
        result = parser.parse(code)
        
        assert len(result.functions) == 1
        assert result.functions[0].is_async is True
    
    def test_parse_class(self, parser):
        """Test parsing a class."""
        code = """
class Calculator:
    '''A simple calculator.'''
    
    def add(self, a, b):
        return a + b
    
    def subtract(self, a, b):
        return a - b
"""
        result = parser.parse(code)
        
        assert len(result.classes) == 1
        cls = result.classes[0]
        assert cls.name == "Calculator"
        assert cls.docstring == "A simple calculator."
        assert len(cls.methods) == 2
        assert cls.methods[0].name == "add"
        assert cls.methods[1].name == "subtract"
    
    def test_parse_class_with_inheritance(self, parser):
        """Test parsing class with base classes."""
        code = """
class Dog(Animal):
    pass
"""
        result = parser.parse(code)
        
        assert len(result.classes) == 1
        assert result.classes[0].bases == ["Animal"]
    
    def test_parse_imports(self, parser):
        """Test parsing import statements."""
        code = """
import os
import sys
from pathlib import Path
from typing import List, Dict
"""
        result = parser.parse(code)
        
        assert len(result.imports) == 4
        
        # Check import os
        assert result.imports[0].module == "os"
        assert result.imports[0].is_from_import is False
        
        # Check from pathlib import Path
        assert result.imports[2].module == "pathlib"
        assert result.imports[2].names == ["Path"]
        assert result.imports[2].is_from_import is True
    
    def test_parse_decorated_function(self, parser):
        """Test parsing function with decorators."""
        code = """
@property
def name(self):
    return self._name
"""
        result = parser.parse(code)
        
        assert len(result.functions) == 1
        assert "property" in result.functions[0].decorators[0]
    
    def test_parse_module_docstring(self, parser):
        """Test extracting module docstring."""
        code = '''
"""
This is a module docstring.
It explains what the module does.
"""

def func():
    pass
'''
        result = parser.parse(code)
        
        assert result.docstring is not None
        assert "module docstring" in result.docstring
    
    def test_parse_empty_code(self, parser):
        """Test parsing empty code."""
        result = parser.parse("")
        
        assert len(result.functions) == 0
        assert len(result.classes) == 0
        assert result.error is None
    
    def test_parse_syntax_error(self, parser):
        """Test parsing code with syntax error."""
        code = """
    def broken(
        # Missing closing parenthesis
    """
        result = parser.parse(code)
        
        assert result.error is not None
        # Just check that there IS an error, don't check exact message
        assert len(result.error) > 0
    
    def test_line_numbers(self, parser):
        """Test that line numbers are captured correctly."""
        code = """
def func1():
    pass

def func2():
    pass
"""
        result = parser.parse(code)
        
        assert len(result.functions) == 2
        assert result.functions[0].line_start == 2
        assert result.functions[1].line_start == 5
    
    def test_total_lines(self, parser):
        """Test that total lines are counted."""
        code = """
        def func():
            pass
        """
        result = parser.parse(code)
        
        assert result.total_lines == 4  # Including blank lines


class TestComplexScenarios:
    """Test more complex parsing scenarios."""
    
    @pytest.fixture
    def parser(self):
        return PythonParser()
    
    def test_nested_functions_extracted(self, parser):
        """Test that nested functions ARE extracted (for code review)."""
        code = """
def outer():
    def inner():
        pass
    return inner
"""
        result = parser.parse(code)
        
        # Should get BOTH outer and inner functions
        assert len(result.functions) == 2
        assert result.functions[0].name == "outer"
        assert result.functions[1].name == "inner"
    
    def test_multiple_decorators(self, parser):
        """Test function with multiple decorators."""
        code = """
@decorator1
@decorator2
def func():
    pass
"""
        result = parser.parse(code)
        
        assert len(result.functions[0].decorators) == 2
    
    def test_type_hints(self, parser):
        """Test parsing functions with type hints."""
        code = """
def greet(name: str) -> str:
    return f"Hello, {name}"
"""
        result = parser.parse(code)
        
        func = result.functions[0]
        assert func.returns == "str"