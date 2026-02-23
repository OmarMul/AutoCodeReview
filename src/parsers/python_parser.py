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
    names: List[str]
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
    def parse(self, code: str, filename: str = "<string>") -> ParseResult:
        """
        Parse Python code and extract structure.
        
        Args:
            code: Python source code as string
            filename: Filename for error messages
        
        Returns:
            ParseResult: Extracted code information
        """
        result = ParseResult()
        
        # Handle empty code
        if not code or not code.strip():
            logger.warning(f"Empty code provided for {filename}")
            return result
        
        # Count total lines
        result.total_lines = len(code.splitlines())
        
        try:
            # Parse code into AST
            tree = ast.parse(code, filename=filename)
            
            # Extract module docstring
            result.docstring = ast.get_docstring(tree)
            
            # Walk through AST nodes
            for node in ast.walk(tree):
                # Extract ALL functions (including nested, but not methods)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Skip if it's a method (will be extracted with class)
                    if not self._is_method(node, tree):
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
            # Capture the actual error message
            error_msg = str(e)
            logger.error(f"Syntax error in {filename}: {error_msg}")
            result.error = error_msg
        
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error parsing {filename}: {error_msg}")
            result.error = error_msg
        
        return result

    def _is_method(self, node: ast.AST, tree: ast.AST) -> bool:
        """Check if function is a method inside a class."""
        for parent in ast.walk(tree):
            if isinstance(parent, ast.ClassDef):
                for child in ast.walk(parent):
                    if child is node:
                        return True
        return False
    

    def _extract_function(self, node: ast.FunctionDef)-> FunctionInfo:
        """Extract function information"""
        name = node.name
        
        line_start = node.lineno
        line_end = node.end_lineno
        
        args = [arg.arg for arg in node.args.args]
        
        returns = None
        if node.returns:
            returns = ast.unparse(node.returns) if hasattr(ast, 'unparse') else ast.dump(node.returns)
        
        docstring = ast.get_docstring(node)
        
        decorators = [ast.unparse(dec) if hasattr(ast, 'unparse') else dec.id for dec in node.decorator_list]
        
        is_async = isinstance(node, ast.AsyncFunctionDef)
        
        return FunctionInfo(
            name=name,
            line_start=line_start,
            line_end=line_end,
            args=args,
            returns=returns,
            docstring=docstring,
            decorators=decorators,
            is_async=is_async,
        )
    
    def _extract_class(self, node: ast.ClassDef) -> ClassInfo:
        """Extract class information"""
        name = node.name
        
        line_start = node.lineno
        line_end = node.end_lineno or line_start

        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(ast.unparse(base) if hasattr(ast, 'unparse') else str(base))
        methods = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                mrthod_indo = self._extract_function(item)
                methods.append(mrthod_indo)
        
        docstring = ast.get_docstring(node)
        decorators = [ast.unparse(dec) if hasattr(ast, 'unparse') else dec.id for dec in node.decorator_list]
        
        return ClassInfo(
            name=name,
            line_start=line_start,
            line_end=line_end,
            bases=bases,
            methods=methods,
            docstring=docstring,
            decorators=decorators,
        )
    
    def _extract_import(self, node: ast.Import) -> ImportInfo:
        """Extract import information"""
        names = [alias.name for alias in node.names]
        module = names[0] if names else ""
        return ImportInfo(
            module=module,
            names=names,
            line=node.lineno,
            is_from_import=False,
        )
    
    def _extract_import_from(self, node: ast.ImportFrom) -> ImportInfo:
        """Extract import from information" "from ... import ..." """
        module = node.module or ""
        names = [alias.name for alias in node.names]
        
        return ImportInfo(
            module=module,
            names=names,
            line=node.lineno,
            is_from_import=True,
        )