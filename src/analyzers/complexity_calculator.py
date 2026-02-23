"""
Code complexity calculator using radon.
Calculates cyclomatic complexity and maintainability metrics.
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from radon.complexity import cc_visit
from radon.metrics import mi_visit, mi_parameters
from radon.raw import analyze

logger = logging.getLogger(__name__)


@dataclass
class FunctionComplexity:
    """Complexity metrics for a single function."""
    name: str
    complexity: int  # Cyclomatic complexity
    line_start: int
    line_end: int
    rank: str  # A, B, C, D, E, F (A=best, F=worst)


@dataclass
class FileComplexity:
    """Complexity metrics for entire file."""
    functions: List[FunctionComplexity]
    maintainability_index: float  # 0-100 (higher is better)
    lines_of_code: int
    logical_lines: int
    comment_lines: int
    blank_lines: int
    
    @property
    def average_complexity(self) -> float:
        """Calculate average complexity of all functions."""
        if not self.functions:
            return 0.0
        return sum(f.complexity for f in self.functions) / len(self.functions)
    
    @property
    def max_complexity(self) -> int:
        """Get maximum complexity in file."""
        if not self.functions:
            return 0
        return max(f.complexity for f in self.functions)
    
    @property
    def complex_functions(self) -> List[FunctionComplexity]:
        """Get functions with high complexity (>10)."""
        return [f for f in self.functions if f.complexity > 10]


class ComplexityCalculator:
    """Calculate code complexity metrics."""
    
    # Complexity thresholds (standard industry values)
    THRESHOLD_LOW = 5      # A-B: Simple
    THRESHOLD_MEDIUM = 10  # C: Moderate
    THRESHOLD_HIGH = 20    # D-E: Complex
    # F: Very complex (>20)
    
    def calculate(self, code: str, filename: str = "<string>") -> FileComplexity:
        """
        Calculate complexity metrics for code.
        
        Args:
            code: Python source code
            filename: Filename for error messages
        
        Returns:
            FileComplexity: All complexity metrics
        """
        if not code or not code.strip():
            logger.warning(f"Empty code for {filename}")
            return FileComplexity(
                functions=[],
                maintainability_index=100.0,
                lines_of_code=0,
                logical_lines=0,
                comment_lines=0,
                blank_lines=0
            )
        
        try:
            # Calculate cyclomatic complexity for functions
            functions = self._calculate_cyclomatic_complexity(code, filename)
            
            # Calculate maintainability index
            mi = self._calculate_maintainability_index(code)
            
            # Calculate lines of code metrics
            loc_metrics = self._calculate_loc(code)
            
            return FileComplexity(
                functions=functions,
                maintainability_index=mi,
                lines_of_code=loc_metrics['loc'],
                logical_lines=loc_metrics['lloc'],
                comment_lines=loc_metrics['comments'],
                blank_lines=loc_metrics['blank']
            )
        
        except Exception as e:
            logger.error(f"Error calculating complexity for {filename}: {e}")
            # Return empty metrics on error
            return FileComplexity(
                functions=[],
                maintainability_index=0.0,
                lines_of_code=0,
                logical_lines=0,
                comment_lines=0,
                blank_lines=0
            )
    
    def _calculate_cyclomatic_complexity(
        self, 
        code: str, 
        filename: str
    ) -> List[FunctionComplexity]:
        """
        Calculate cyclomatic complexity for each function.
        Uses radon's cc_visit.
        """
        functions = []
        
        try:
            # Get complexity for all functions
            results = cc_visit(code)
            
            for item in results:
                func_complexity = FunctionComplexity(
                    name=item.name,
                    complexity=item.complexity,
                    line_start=item.lineno,
                    line_end=item.endline,
                    rank=item.letter  # A, B, C, D, E, F
                )
                functions.append(func_complexity)
                
                # Log high complexity functions
                if item.complexity > self.THRESHOLD_MEDIUM:
                    logger.info(
                        f"High complexity function: {item.name} "
                        f"(complexity={item.complexity}, rank={item.letter})"
                    )
        
        except Exception as e:
            logger.error(f"Error calculating cyclomatic complexity: {e}")
        
        return functions
    
    def _calculate_maintainability_index(self, code: str) -> float:
        """
        Calculate maintainability index (0-100).
        Higher is better.
        
        Ranges:
        - 85-100: Highly maintainable
        - 65-84: Moderately maintainable  
        - 0-64: Difficult to maintain
        """
        try:
            # Calculate MI using radon
            mi = mi_visit(code, multi=False)
            return round(mi, 2)
        except Exception as e:
            logger.error(f"Error calculating maintainability index: {e}")
            return 0.0
    
    def _calculate_loc(self, code: str) -> Dict[str, int]:
        """
        Calculate lines of code metrics.
        
        Returns:
            dict with keys: loc, lloc, comments, blank
        """
        try:
            # Use radon's analyze function
            raw = analyze(code)
            
            return {
                'loc': raw.loc,           # Total lines
                'lloc': raw.lloc,         # Logical lines (actual code)
                'comments': raw.comments, # Comment lines
                'blank': raw.blank        # Blank lines
            }
        except Exception as e:
            logger.error(f"Error calculating LOC: {e}")
            return {'loc': 0, 'lloc': 0, 'comments': 0, 'blank': 0}
    
    def get_complexity_rating(self, complexity: int) -> str:
        """
        Get human-readable rating for complexity value.
        
        Args:
            complexity: Cyclomatic complexity value
        
        Returns:
            Rating string
        """
        if complexity <= self.THRESHOLD_LOW:
            return "Simple"
        elif complexity <= self.THRESHOLD_MEDIUM:
            return "Moderate"
        elif complexity <= self.THRESHOLD_HIGH:
            return "Complex"
        else:
            return "Very Complex"