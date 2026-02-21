import ast
from src.utils.logger import get_logger
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

logger = get_logger(__name__)

@dataclass
class FunctionInfo:
    """Information about function"""
    name: str
    line_start: int
    line_end: int
    args: List[str]
    returns: Optional[str]
    docstring: Optional[str]
    decorators: List[str]
    is_async: bool
    complexity: int = 0

@dataclass
class ClassInfo:
    """Information about class"""
    name: str
    line_start: int
    line_end: int
    bases: List[str]
    methods: List[FunctionInfo]
    docstring: Optional[str]
    decorators: List[str]

@dataclass
class ImportInfo:
    """Information about import"""
    module: str
    name: str
    line: int
    is_from_import: bool
    
@dataclass
class ParseResult:
    """Result of parsing a Python file"""
    functions: List[FunctionInfo] = field(default_factory=list)
    classes: List[ClassInfo] = field(default_factory=list)
    imports: List[ImportInfo] = field(default_factory=list)
    docstring: Optional[str] = None
    total_lines: int = 0
    error: Optional[str] = None

class PythonParser:
    """Parse Python files"""
    def parse(self, code: str, filename:str = "<string>") -> ParseResult:
        """Parse Python code"""
        result = ParseResult()
        #Handle Empty code
        if not code.strip():
            logger.warning(f"Empty code provided for {filename}")
            return result
        #count totola line
        result.total_lines = len(code.splitlines())

        try:
            #parse code into AST
            tree = ast.parse(code, filename=filename)
            
            #extract docstring
            result.docstring = ast.get_docstring(tree)

            #walk through AST nodes
            for node in ast.walk(tree):
                #exratract functions
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # get only top_level functions
                    func_info = self._extract_function(node)
                    result.functions.append(func_info)
                # Extract classes
                elif isinstance(node, ast.ClassDef):
                    class_info = self._extract_class(node)
                    result.classes.append(class_info)
                
                # Extract imports
                elif isinstance(node, ast.Import):
                    import_info = self._extract_import(node)
                    result.imports.append(import_info)
                
                elif isinstance(node, ast.ImportFrom):
                    import_info = self._extract_import_from(node)
                    result.imports.append(import_info)
            
            logger.info(
                f"Parsed {filename}: "
                f"{len(result.functions)} functions, "
                f"{len(result.classes)} classes, "
                f"{len(result.imports)} imports"
            )
        except SyntaxError as e:
            logger.error(f"Syntax error in {filename}: {e}")
            result.error = str(e)
        except Exception as e:
            logger.error(f"Error parsing {filename}: {e}")
            result.error = str(e)
        
        return result