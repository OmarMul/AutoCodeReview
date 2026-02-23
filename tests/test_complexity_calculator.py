"""
Tests for complexity calculator.
"""

import pytest
from src.analyzers.complexity_calculator import ComplexityCalculator


class TestComplexityCalculator:
    """Test complexity calculation."""
    
    @pytest.fixture
    def calculator(self):
        """Create calculator instance."""
        return ComplexityCalculator()
    
    def test_simple_function(self, calculator):
        """Test complexity of simple function."""
        code = """
def simple():
    return 42
"""
        result = calculator.calculate(code)
        
        assert len(result.functions) == 1
        assert result.functions[0].name == "simple"
        assert result.functions[0].complexity == 1  # Simple function
    
    def test_complex_function(self, calculator):
        """Test complexity of function with branches."""
        code = """
def complex_function(x):
    if x > 0:
        if x > 10:
            return "big"
        else:
            return "small"
    elif x < 0:
        return "negative"
    else:
        return "zero"
"""
        result = calculator.calculate(code)
        
        func = result.functions[0]
        assert func.name == "complex_function"
        assert func.complexity > 1  # Has branches
    
    def test_multiple_functions(self, calculator):
        """Test file with multiple functions."""
        code = """
def func1():
    pass

def func2():
    if True:
        return 1
    return 0

def func3():
    for i in range(10):
        if i > 5:
            break
"""
        result = calculator.calculate(code)
        
        assert len(result.functions) == 3
        assert result.average_complexity > 0
    
    def test_maintainability_index(self, calculator):
        """Test maintainability index calculation."""
        code = """
def well_written():
    '''Good docstring.'''
    x = 1
    y = 2
    return x + y
"""
        result = calculator.calculate(code)
        
        # Well-written code should have high MI
        assert result.maintainability_index > 50
    
    def test_lines_of_code(self, calculator):
        """Test LOC metrics."""
        code = """
# Comment line

def function():
    # Another comment
    x = 1
    
    y = 2
    return x + y
"""
        result = calculator.calculate(code)
        
        assert result.lines_of_code > 0
        assert result.comment_lines >= 2
        assert result.blank_lines >= 1
    
    def test_complex_functions_filter(self, calculator):
        """Test filtering complex functions."""
        code = """
def simple():
    return 1

def complex():
    for i in range(10):
        if i > 5:
            for j in range(i):
                if j % 2:
                    print(j)
"""
        result = calculator.calculate(code)
        
        # Only complex() should be flagged
        complex_funcs = result.complex_functions
        assert len(complex_funcs) >= 1
        assert any(f.name == "complex" for f in complex_funcs)
    
    def test_empty_code(self, calculator):
        """Test empty code handling."""
        result = calculator.calculate("")
        
        assert len(result.functions) == 0
        assert result.maintainability_index == 100.0
    
    def test_max_complexity(self, calculator):
        """Test finding max complexity."""
        code = """
def low():
    return 1

def high():
    if True:
        for i in range(10):
            if i > 5:
                return i
"""
        result = calculator.calculate(code)
        
        assert result.max_complexity > 1
    
    def test_complexity_rating(self, calculator):
        """Test complexity rating strings."""
        assert calculator.get_complexity_rating(3) == "Simple"
        assert calculator.get_complexity_rating(7) == "Moderate"
        assert calculator.get_complexity_rating(15) == "Complex"
        assert calculator.get_complexity_rating(25) == "Very Complex"