"""
Unified analysis pipeline that orchestrates all code analyzers.
Coordinates parsing, complexity analysis, and security scanning.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from src.utils.logger import get_logger
from src.parsers.python_parser import PythonParser, ParseResult
from src.analyzers.complexity_calculator import (
    ComplexityCalculator,
    FileComplexity,
    FunctionComplexity
)
from src.analyzers.security_scanner import (
    SecurityScanner,
    SecurityScanResult,
    SecurityIssue,
    Severity
)
from src.utils.diff_parser import DiffParser, ChangedFile

logger = get_logger(__name__)


class AnalysisStatus(Enum):
    """Status of analysis operation."""
    PENDING = "pending"
    PARSING = "parsing"
    ANALYZING_COMPLEXITY = "analyzing_complexity"
    SCANNING_SECURITY = "scanning_security"
    AGGREGATING = "aggregating"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class AnalysisProgress:
    """Progress of analysis operation."""
    status: AnalysisStatus
    current_step: str
    total_steps: int
    completed_steps: int
    percentage: float
    message: str = ""

    def update(
        self,
        status: Optional[AnalysisStatus] = None,
        step: Optional[str] = None,
        message: Optional[str] = None,
    ):
        """Update progress of analysis operation."""
        if status:
            self.status = status
        if step:
            self.current_step = step
            self.completed_steps += 1
        if message:
            self.message = message
        self.percentage = (self.completed_steps / self.total_steps) * 100

@dataclass
class FunctionAnalysis:
    """Complete analysis for a single function."""
    name: str
    line_start: int
    line_end: int

    #from parser
    args: List[str] = field(default_factory=list)
    returns: Optional[str] = None
    docstring: Optional[str] = None
    decorators: List[str] = field(default_factory=list)
    is_async: bool = False

    # From complexity calculator
    complexity: int = 0
    complexity_rank: str = "A"
    
    # From security scanner
    security_issues: List[SecurityIssue] = field(default_factory=list)
    
    # Analysis flags
    is_complex: bool = False
    is_undocumented: bool = False
    has_security_issues: bool = False
    has_critical_security_issues: bool = False
    
    # Changed in PR (from diff)
    is_changed: bool = False

    @property
    def needs_attention(self) -> bool:
        """Check if function needs attention."""
        return(
            self.is_complex or
            self.has_critical_security_issues or
            (self.is_undocumented and self.is_changed)
        )
    
    def get_issues_summary(self) -> str:
        """Get human-readable summary of issues."""
        issues = []
        if self.is_complex:
            issues.append(f"High complexity: {self.complexity}")

        if self.is_undocumented:
            issues.append("Missing documentation")

        if self.has_security_issues:
            critical = sum(1 for i in self.security_issues if i.is_critical)
            issues.append(f"{critical} critical security issue(s)")
        elif self.has_security_issues:
            issues.append(f"{len(self.security_issues)} security issue(s)")
        
        return ", ".join(issues) if issues else "No issues"

@dataclass
class FileAnalysis:
    """Complete analysis for a single file."""
    filename: str
    language: str = "python"
    source_code: str = ""
    # Raw results
    parse_result: Optional[ParseResult] = None
    complexity_result: Optional[FileComplexity] = None
    security_result: Optional[SecurityScanResult] = None
    
    # Aggregated function analyses
    functions: List[FunctionAnalysis] = field(default_factory=list)
    
    # File-level metrics
    total_lines: int = 0
    total_functions: int = 0
    total_classes: int = 0
    
    # Quality metrics
    average_complexity: float = 0.0
    max_complexity: int = 0
    maintainability_index: float = 0.0
    
    # Security metrics
    total_security_issues: int = 0
    critical_security_issues: int = 0
    high_severity_issues: int = 0
    
    # Analysis metadata
    analysis_time: float = 0.0
    error: Optional[str] = None
    
    # Changed in PR
    is_changed: bool = False
    changed_line_numbers: set = field(default_factory=set)
    
    @property
    def has_errors(self) -> bool:
        """Check if analysis had errors."""
        return self.error is not None
    
    @property
    def quality_score(self) -> float:
        """
        Calculate overall quality score (0-100).
        Higher is better.
        """
        if self.has_errors:
            return 0.0
        
        # Start with maintainability index
        score = self.maintainability_index if self.maintainability_index else 50.0
        
        # Penalize for complexity
        if self.average_complexity > 10:
            score -= (self.average_complexity - 10) * 2
        
        # Penalize for security issues
        score -= self.critical_security_issues * 10
        score -= self.high_severity_issues * 5
        
        # Clamp to 0-100
        return max(0.0, min(100.0, score))
    
    def get_functions_needing_attention(self) -> List[FunctionAnalysis]:
        """Get functions that need attention."""
        return [f for f in self.functions if f.needs_attention]
    
    def get_summary(self) -> Dict[str, Any]:
        """Get human-readable summary."""
        return {
            'filename': self.filename,
            'language': self.language,
            'total_lines': self.total_lines,
            'total_functions': self.total_functions,
            'total_classes': self.total_classes,
            'average_complexity': round(self.average_complexity, 2),
            'max_complexity': self.max_complexity,
            'maintainability_index': round(self.maintainability_index, 2),
            'quality_score': round(self.quality_score, 2),
            'total_security_issues': self.total_security_issues,
            'critical_security_issues': self.critical_security_issues,
            'functions_needing_attention': len(self.get_functions_needing_attention()),
            'is_changed': self.is_changed,
            'analysis_time': round(self.analysis_time, 2)
        }

@dataclass
class AnalysisBatchResult:
    """Result of analyzing multiple files."""
    files: List[FileAnalysis] = field(default_factory=list)
    total_analysis_time: float = 0.0
    
    @property
    def total_files(self) -> int:
        """Total files analyzed."""
        return len(self.files)
    
    @property
    def total_issues(self) -> int:
        """Total issues found across all files."""
        return sum(f.total_security_issues for f in self.files)
    
    @property
    def total_critical_issues(self) -> int:
        """Total critical issues."""
        return sum(f.critical_security_issues for f in self.files)
    
    @property
    def average_quality_score(self) -> float:
        """Average quality score across all files."""
        if not self.files:
            return 0.0
        return sum(f.quality_score for f in self.files) / len(self.files)
    
    def get_files_with_issues(self) -> List[FileAnalysis]:
        """Get files that have issues."""
        return [f for f in self.files if f.total_security_issues > 0]
    
    def get_summary(self) -> Dict[str, Any]:
        """Get overall summary."""
        return {
            'total_files': self.total_files,
            'total_issues': self.total_issues,
            'total_critical_issues': self.total_critical_issues,
            'average_quality_score': round(self.average_quality_score, 2),
            'files_with_issues': len(self.get_files_with_issues()),
            'total_analysis_time': round(self.total_analysis_time, 2)
        }

class AnalysisPipeline:
    """Unified analysis pipeline that orchestrates all code analyzers."""
    def __init__(
        self,
        enable_async: bool = False,
        complexity_threshold: int = 5,
        enable_caching: bool = True,
        ):

        self.parser = PythonParser()
        self.complexity_calculator = ComplexityCalculator()
        self.security_analyzer = SecurityScanner()
        self.diff_parser = DiffParser()
        #config
        self.enable_async = enable_async
        self.complexity_threshold = complexity_threshold
        self.enable_caching = enable_caching

        logger.info(
            f"Initialized AnalysisPipeline "
            f"(async={enable_async}, caching={enable_caching})"
        )

    def analyze_file(
        self,
        code: str,
        filename: str = "code.py",
        changed_lines: Optional[set] = None,
        progress_callback: Optional[callable] = None,
    ) -> FileAnalysis:
        """Analyze a single file."""
        start_time = time.time()

        #Initialize progress
        progress = AnalysisProgress(
            status=AnalysisStatus.PENDING,
            current_step="Initializing",
            total_steps=4,
            completed_steps=0,
            percentage=0,
        )
        if progress_callback:
            progress_callback(progress)

        try:
            #Step 1: Parse code
            progress.update(
                status=AnalysisStatus.PARSING,
                step="Parsing code structure",
                message=f"Parsing {filename}"
            )
            parse_result = self.parser.parse(code, filename)

            if parse_result.error:
                logger.error(f"Parse error in {filename}: {parse_result.error}")
                return FileAnalysis(
                    filename=filename,
                    error=parse_result.error,
                    analysis_time=time.time() - start_time
                )

            #Step 2: Calculate complexity
            progress.update(
                status=AnalysisStatus.ANALYZING_COMPLEXITY,
                step="Calculating cyclomatic complexity",
                message=f"Calculating cyclomatic complexity for {filename}"
            )
            if progress_callback:
                progress_callback(progress)
            complexity_result = self.complexity_calculator.calculate(code, filename)
            
            #Step 3: Analyze security
            progress.update(
                status=AnalysisStatus.SCANNING_SECURITY,
                step="Scanning for security issues",
                message="Running Bandit security scan"
            )
            if progress_callback:
                progress_callback(progress)
            
            security_result = self.security_analyzer.scan(code, filename)


            #step 4: Aggregate results
            progress.update(
                status=AnalysisStatus.AGGREGATING,
                step="Aggregating results",
                message="Combining analysis results"
            )
            if progress_callback:
                progress_callback(progress)
            
            file_analysis = self._aggregate_results(
                filename=filename,
                parse_result=parse_result,
                complexity_result=complexity_result,
                security_result=security_result,
                changed_lines=changed_lines
            )
            file_analysis.source_code = code
            file_analysis.analysis_time = time.time() - start_time
            
            #complete
            progress.update(
                status=AnalysisStatus.COMPLETED,
                step="Analysis completed",
                message=f"Analysis complete in {file_analysis.analysis_time:.2f}s"
            )
            if progress_callback:
                progress_callback(progress)
            logger.info(
                f"Analyzed {filename}: "
                f"{file_analysis.total_functions} functions, "
                f"{file_analysis.total_security_issues} security issues, "
                f"quality score: {file_analysis.quality_score:.1f}"
            )

            return file_analysis
        
        except Exception as e:
            logger.error(f"Analysis failed for {filename}: {e}", exc_info=True)
            progress.update(
                status=AnalysisStatus.FAILED,
                message=f"Analysis failed for {filename}: {e}"
            )
            if progress_callback:
                progress_callback(progress)
            
            return FileAnalysis(
                filename=filename,
                error=str(e),
                analysis_time=time.time() - start_time
            )
    async def analyze_file_async(
        self,
        code: str,
        filename: str = "code.py",
        changed_lines: Optional[set] = None,
        progress_callback: Optional[callable] = None,
    ) -> FileAnalysis:
        """Analyze a single file asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.analyze_file,
            code,
            filename,
            changed_lines,
            progress_callback,
        )
    
    def analyse_batch(
        self,
        files: List[Dict[str, Any]],
        progress_callback: Optional[callable] = None,
    ) -> AnalysisBatchResult:
        """Analyze a multiple files."""
        start_time = time.time()
        if self.enable_async:
            return asyncio.run(
                self.analyse_batch_async(files, progress_callback)
            )
        else:
            #sequential
            results = []
            for file_data in files:
                result = self.analyze_file(
                    code=file_data['code'],
                    filename=file_data['filename'],
                    changed_lines=file_data.get('changed_lines'),
                    progress_callback=progress_callback,
                )
                results.append(result)
            return AnalysisBatchResult(
                files=results,
                total_analysis_time=time.time() - start_time,
            )
    
    async def analyse_batch_async(
        self,
        files: List[Dict[str, Any]],
        progress_callback: Optional[callable] = None,
    ) -> AnalysisBatchResult:
        """Analyze a multiple files asynchronously."""
        start_time = time.time()
        
        #create tasks
        tasks = [
            self.analyze_file_async(
                code=file_data['code'],
                filename=file_data['filename'],
                changed_lines=file_data.get('changed_lines'),
                progress_callback=progress_callback,
            )
            for file_data in files
        ]
        
        #run tasks in parallel
        results = await asyncio.gather(*tasks)
        
        return AnalysisBatchResult(
            files=results,
            total_analysis_time=time.time() - start_time,
        )
    
    def analyze_pr_changes(
        self,
        diff_text: str,
        get_file_content: callable,
        progress_callback: Optional[callable] = None,
    ) -> AnalysisBatchResult:
        """Analyze changes in a pull request."""
        logger.info("Analyzing pull request changes")

        #parse diff
        diff_result = self.diff_parser.parse_diff(diff_text)
        python_files = diff_result.get_python_files()

        if not python_files:
            logger.warning("No python files found in diff")
            return AnalysisBatchResult(
                files=[],
                analysis_time=0.0,
            )
        
        #prepare files for analysis
        files_to_analyze = []
        for file_change in python_files:
            if file_change.is_deleted_file or file_change.is_binary:
                continue

            try:
                code = get_file_content(file_change.filename)
                files_to_analyze.append(
                    {
                        'code': code,
                        'filename': file_change.filename,
                        'changed_lines': file_change.changed_line_numbers()
                    }
                )
            except Exception as e:
                logger.error(f"Failed to read file {file_change.filename}: {e}")
                continue
        
        #analyze files
        return self.analyse_batch(
            files=files_to_analyze,
            progress_callback=progress_callback,
        )
    
    def _aggregate_results(
        self,
        filename: str,
        parse_result: ParseResult,
        complexity_result: FileComplexity,
        security_result: SecurityScanResult,
        changed_lines: Optional[set] = None,
    ) -> FileAnalysis:
        """Aggregate results from different analyzers."""
        
        functions = []
        for parsed_func in parse_result.functions:
            complexity_data = next(
                (c for c in complexity_result.functions if c.name == parsed_func.name),
                None
            )

            #find security issues
            func_security_issues = [
                issue for issue in security_result.issues
                if parsed_func.line_start <= issue.line_number <= parsed_func.line_end
            ]

            #check if function is changed
            func_changed = False
            if changed_lines:
                func_changed = any(
                    parsed_func.line_start <= line <= parsed_func.line_end
                    for line in changed_lines
                )
            
            # Create function analysis
            func_analysis = FunctionAnalysis(
                name=parsed_func.name,
                line_start=parsed_func.line_start,
                line_end=parsed_func.line_end,
                args=parsed_func.args,
                returns=parsed_func.returns,
                docstring=parsed_func.docstring,
                decorators=parsed_func.decorators,
                is_async=parsed_func.is_async,
                complexity=complexity_data.complexity if complexity_data else 0,
                complexity_rank=complexity_data.rank if complexity_data else "A",
                security_issues=func_security_issues,
                is_complex=complexity_data.complexity > self.complexity_threshold if complexity_data else False,
                is_undocumented=not parsed_func.docstring,
                has_security_issues=len(func_security_issues) > 0,
                has_critical_security_issues=any(i.is_critical for i in func_security_issues),
                is_changed=func_changed
            )
            functions.append(func_analysis)


        # Create file analysis
        file_analysis = FileAnalysis(
            filename=filename,
            language="python",
            parse_result=parse_result,
            complexity_result=complexity_result,
            security_result=security_result,
            functions=functions,
            total_lines=parse_result.total_lines,
            total_functions=len(parse_result.functions),
            total_classes=len(parse_result.classes),
            average_complexity=complexity_result.average_complexity,
            max_complexity=complexity_result.max_complexity,
            maintainability_index=complexity_result.maintainability_index,
            total_security_issues=security_result.metrics.total_issues,
            critical_security_issues=security_result.metrics.critical_issues,
            high_severity_issues=security_result.metrics.high_severity,
            is_changed=bool(changed_lines),
            changed_line_numbers=changed_lines or set()
        )
        
        return file_analysis
    
    def generate_report(
        self,
        analysis: FileAnalysis,
        format: str = "text"
    ) -> str:
        """
        Generate human-readable report.
        
        Args:
            analysis: File analysis results
            format: Report format - "text" or "markdown"
        
        Returns:
            Formatted report
        """
        if format == "markdown":
            return self._generate_markdown_report(analysis)
        else:
            return self._generate_text_report(analysis)
    
    def _generate_text_report(self, analysis: FileAnalysis) -> str:
        """Generate plain text report."""
        lines = []
        lines.append("=" * 70)
        lines.append(f"ANALYSIS REPORT: {analysis.filename}")
        lines.append("=" * 70)
        lines.append("")
        
        # Summary
        summary = analysis.get_summary()
        lines.append("SUMMARY")
        lines.append("-" * 70)
        lines.append(f"Total Functions: {summary['total_functions']}")
        lines.append(f"Total Classes: {summary['total_classes']}")
        lines.append(f"Total Lines: {summary['total_lines']}")
        lines.append(f"Average Complexity: {summary['average_complexity']}")
        lines.append(f"Max Complexity: {summary['max_complexity']}")
        lines.append(f"Maintainability Index: {summary['maintainability_index']}")
        lines.append(f"Quality Score: {summary['quality_score']}/100")
        lines.append(f"Security Issues: {summary['total_security_issues']}")
        lines.append(f"Critical Issues: {summary['critical_security_issues']}")
        lines.append("")
        
        # Functions needing attention
        needs_attention = analysis.get_functions_needing_attention()
        if needs_attention:
            lines.append("FUNCTIONS NEEDING ATTENTION")
            lines.append("-" * 70)
            for func in needs_attention:
                lines.append(f"\n{func.name} (Line {func.line_start}-{func.line_end})")
                lines.append(f"  Issues: {func.get_issues_summary()}")
        
        lines.append("")
        lines.append("=" * 70)
        
        return "\n".join(lines)
    
    def _generate_markdown_report(self, analysis: FileAnalysis) -> str:
        """Generate Markdown report."""
        lines = []
        lines.append(f"# Analysis Report: {analysis.filename}")
        lines.append("")
        
        # Summary
        summary = analysis.get_summary()
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- **Quality Score:** {summary['quality_score']}/100")
        lines.append(f"- **Maintainability Index:** {summary['maintainability_index']}")
        lines.append(f"- **Functions:** {summary['total_functions']}")
        lines.append(f"- **Classes:** {summary['total_classes']}")
        lines.append(f"- **Average Complexity:** {summary['average_complexity']}")
        lines.append(f"- **Security Issues:** {summary['total_security_issues']} ({summary['critical_security_issues']} critical)")
        lines.append("")
        
        # Functions
        needs_attention = analysis.get_functions_needing_attention()
        if needs_attention:
            lines.append("## Functions Needing Attention")
            lines.append("")
            for func in needs_attention:
                lines.append(f"### `{func.name}` (Lines {func.line_start}-{func.line_end})")
                lines.append("")
                lines.append(f"**Issues:** {func.get_issues_summary()}")
                lines.append("")
        
        return "\n".join(lines)