import json
import subprocess
import tempfile
import os
from typing import List, Optional, Dict, Set, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
from src.utils.logger import get_logger
from src.utils.cache import cache_analysis_result

logger = get_logger(__name__)


class Severity(Enum):
    """Security issue severity levels."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNDEFINED = "UNDEFINED"


class Confidence(Enum):
    """Confidence level in the security finding."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNDEFINED = "UNDEFINED"


@dataclass
class SecurityIssue:
    """Represents a security vulnerability found in code."""

    # Identification
    test_id: str
    test_name: str

    # Severity and confidence
    severity: Severity
    confidence: Confidence

    # Location
    line_number: int

    # Code details (REQUIRED → must be before defaults)
    code: str

    # Optional fields (defaults below)
    line_range: List[int] = field(default_factory=list)
    filename: str = "code.py"

    # Issue details
    message: str = ""
    cwe_id: Optional[str] = None
    more_info: str = ""

    # Context
    col_offset: int = 0

    def __post_init__(self):
        """Convert string values to enums if needed."""
        if isinstance(self.severity, str):
            try:
                self.severity = Severity[self.severity]
            except KeyError:
                self.severity = Severity.UNDEFINED
        
        if isinstance(self.confidence, str):
            try:
                self.confidence = Confidence[self.confidence]
            except KeyError:
                self.confidence = Confidence.UNDEFINED
    
    @property
    def is_critical(self) -> bool:
        """Check if the issue is critical."""
        return (
            self.severity == Severity.HIGH and
            self.confidence == Confidence.HIGH

        )
    
    @property
    def is_high_severity(self) -> bool:
        """Check if this is a high severity issue."""
        return self.severity == Severity.HIGH
    
    @property
    def is_medium_severity(self) -> bool:
        """Check if this is a medium severity issue."""
        return self.severity == Severity.MEDIUM
    
    @property
    def is_low_severity(self) -> bool:
        """Check if this is a low severity issue."""
        return self.severity == Severity.LOW

    @property
    def priority_score(self) -> int:
        """
        Calculate priority score for sorting issues.
        Higher score = higher priority.
        """
        severity_scores = {
            Severity.HIGH: 100,
            Severity.MEDIUM: 50,
            Severity.LOW: 10,
            Severity.UNDEFINED: 0
        }
        
        confidence_scores = {
            Confidence.HIGH: 10,
            Confidence.MEDIUM: 5,
            Confidence.LOW: 1,
            Confidence.UNDEFINED: 0
        }
        
        return severity_scores[self.severity] + confidence_scores[self.confidence]
    def get_category(self) -> str:
        """
        Get vulnerability category from test_id.
        """
        categories = {
            'B1': 'Input Validation',
            'B2': 'SQL Injection',
            'B3': 'Command Injection',
            'B4': 'Cryptography',
            'B5': 'Authentication',
            'B6': 'Code Injection',
            'B7': 'Information Disclosure',
        }
        prefix = self.test_id[:2] if len(self.test_id) >= 2 else ""
        return categories.get(prefix, "General Security")
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'test_id': self.test_id,
            'test_name': self.test_name,
            'severity': self.severity.value,
            'confidence': self.confidence.value,
            'line_number': self.line_number,
            'line_range': self.line_range,
            'code': self.code,
            'filename': self.filename,
            'message': self.message,
            'cwe_id': self.cwe_id,
            'more_info': self.more_info,
            'category': self.get_category(),
            'is_critical': self.is_critical,
            'priority_score': self.priority_score
        }


@dataclass
class SecurityMetrics:
    """Aggregated security metrics."""
    total_lines_scanned: int = 0
    total_issues: int = 0
    
    # By severity
    high_severity: int = 0
    medium_severity: int = 0
    low_severity: int = 0
    undefined_severity: int = 0
    
    # By confidence
    high_confidence: int = 0
    medium_confidence: int = 0
    low_confidence: int = 0
    undefined_confidence: int = 0
    
    # Critical issues (high severity + high confidence)
    critical_issues: int = 0
    
    # By category
    issues_by_category: Dict[str, int] = field(default_factory=dict)
    
    # By test ID
    issues_by_test: Dict[str, int] = field(default_factory=dict)
    
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'total_lines_scanned': self.total_lines_scanned,
            'total_issues': self.total_issues,
            'by_severity': {
                'high': self.high_severity,
                'medium': self.medium_severity,
                'low': self.low_severity,
                'undefined': self.undefined_severity
            },
            'by_confidence': {
                'high': self.high_confidence,
                'medium': self.medium_confidence,
                'low': self.low_confidence,
                'undefined': self.undefined_confidence
            },
            'critical_issues': self.critical_issues,
            'issues_by_category': self.issues_by_category,
            'issues_by_test': self.issues_by_test
        }


@dataclass
class SecurityScanResult:
    """Complete security scan result with detailed analysis."""
    
    # All issues found
    issues: List[SecurityIssue] = field(default_factory=list)
    
    # Aggregated metrics
    metrics: SecurityMetrics = field(default_factory=SecurityMetrics)
    
    # Scan metadata
    scan_time: float = 0.0  # Time taken to scan (seconds)
    bandit_version: str = ""
    errors: List[str] = field(default_factory=list)
    @property
    def has_issues(self) -> bool:
        """Check if any issues were found."""
        return len(self.issues) > 0
    
    @property
    def has_critical_issues(self) -> bool:
        """Check if there are critical issues."""
        return self.metrics.critical_issues > 0
    
    @property
    def has_high_severity_issues(self) -> bool:
        """Check if there are high severity issues."""
        return self.metrics.high_severity > 0


    def get_issues_by_severity(self, severity: Severity) -> List[SecurityIssue]:
        """Get all issues of a specific severity."""
        return [issue for issue in self.issues if issue.severity == severity]
    
    def get_critical_issues(self) -> List[SecurityIssue]:
        """Get all critical issues (high severity + high confidence)."""
        return [issue for issue in self.issues if issue.is_critical]
    
    def get_issues_by_line(self, line_number: int) -> List[SecurityIssue]:
        """Get all issues at a specific line number."""
        return [
            issue for issue in self.issues 
            if issue.line_number == line_number
        ]

    def get_issues_by_category(self, category: str) -> List[SecurityIssue]:
        """Get all issues of a specific category."""
        return [issue for issue in self.issues if issue.get_category() == category]
    
    def get_sorted_issues(self, sort_by = "priority") -> List[SecurityIssue]:
        """Get issues sorted by specified criteria."""
        if sort_by == "priority":
            return sorted(self.issues, key=lambda x: x.priority_score, reverse=True)
        elif sort_by == "severity":
            severity_order = {
                Severity.HIGH: 3,
                Severity.MEDIUM: 2,
                Severity.LOW: 1,
                Severity.UNDEFINED: 0
            }
            return sorted(
                self.issues, 
                key=lambda x: severity_order[x.severity],
                reverse=True
            )
        elif sort_by == "line":
            return sorted(self.issues, key=lambda x: x.line_number)
        elif sort_by == "confidence":
            confidence_order = {
                Confidence.HIGH: 3,
                Confidence.MEDIUM: 2,
                Confidence.LOW: 1,
                Confidence.UNDEFINED: 0
            }
            return sorted(
                self.issues,
                key=lambda x: confidence_order[x.confidence],
                reverse=True
            )
        else:
            return self.issues

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'issues': [issue.to_dict() for issue in self.issues],
            'metrics': self.metrics.to_dict(),
            'scan_time': self.scan_time,
            'bandit_version': self.bandit_version,
            'errors': self.errors,
            'summary': {
                'has_issues': self.has_issues,
                'has_critical_issues': self.has_critical_issues,
                'has_high_severity_issues': self.has_high_severity_issues
            }
        }

class SecurityScanner:
    """
    Comprehensive security scanner using Bandit.
    
    Detects common security vulnerabilities including:
    - Hardcoded passwords and secrets
    - SQL injection vulnerabilities
    - Command injection vulnerabilities
    - Insecure cryptography usage
    - Assert statements in production code
    - Pickle module usage risks
    - Shell command execution risks
    - And many more...
    """
    def __init__(
        self,
        config_file: Optional[str] = None, 
        exclude_tests: Optional[List[str]] = None,
        include_tests: Optional[List[str]] = None,    
    ):
        self.config_file = config_file
        self.exclude_tests = exclude_tests or []
        self.include_tests = include_tests or []
        self._bandit_version = self._get_bandit_version()
        
        logger.info(f"Initialized SecurityScanner with Bandit {self._bandit_version}")
    
    def _get_bandit_version(self) -> str:
        """Get installed Bandit version."""
        try:
            result = subprocess.run(
                ['bandit', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            # Output format: "bandit 1.7.10"
            version = result.stdout.strip().split()[-1] if result.stdout else "unknown"
            return version
        except Exception:
            return "unknown"

    @cache_analysis_result()
    def scan(
        self, code: str,
        filename: str = "code.py",
        severity_level: Optional[Severity] = None,
        confidence_level: Optional[Confidence] = None
    ):
        """
        Scan Python code for security vulnerabilities.
        """

        import time
        start_time = time.time()
        
        if not code or not code.strip():
            logger.warning("Empty code provided for security scan")
            return SecurityScanResult(
                scan_time=0.0,
                bandit_version=self._bandit_version
            )
        
        try:
            # Run Bandit scan
            raw_issues, errors = self._run_bandit(code, filename)
            
            # Parse issues
            issues = self._parse_issues(raw_issues, filename)
            
            # Filter by severity and confidence if specified
            if severity_level:
                issues = [i for i in issues if i.severity.value == severity_level.value]
            
            if confidence_level:
                issues = [i for i in issues if i.confidence.value == confidence_level.value]
            
            # Calculate metrics
            metrics = self._calculate_metrics(issues, code)
            
            # Create result
            scan_time = time.time() - start_time
            result = SecurityScanResult(
                issues=issues,
                metrics=metrics,
                scan_time=scan_time,
                bandit_version=self._bandit_version,
                errors=errors
            )
            
            logger.info(
                f"Security scan complete in {scan_time:.2f}s: "
                f"{result.metrics.total_issues} issues found "
                f"(Critical: {result.metrics.critical_issues}, "
                f"High: {result.metrics.high_severity}, "
                f"Medium: {result.metrics.medium_severity}, "
                f"Low: {result.metrics.low_severity})"
            )
            
            return result
        except Exception as e:
            logger.error(f"Security scan failed: {e}", exc_info=True)
            return SecurityScanResult(
                scan_time=time.time() - start_time,
                bandit_version=self._bandit_version,
                errors=[str(e)]
            )
    def _run_bandit(self, code: str, filename: str) -> Tuple[List[Dict], List[str]]:
        """Run Bandit scan on the code."""
        temp_file = None
        errors = []
        try:
            # write code to temp file
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.py',
                delete=False,
                encoding='utf-8'
            ) as f:
                f.write(code)
                temp_file = f.name
            
            # build bandit command
            cmd = [
                'bandit',
                '-f', 'json',  # JSON format
                '-q',  # Quiet mode
                '-r',  # Recursive (though we're scanning one file)
                temp_file
            ]
            # Add config file if specified
            if self.config_file:
                cmd.extend(['-c', self.config_file])
            # Add test filters
            if self.exclude_tests:
                cmd.extend(['-s', ','.join(self.exclude_tests)])
            if self.include_tests:
                cmd.extend(['-t', ','.join(self.include_tests)])
            
            # run Bandit
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            # parse output
            if result.stdout:
                data = json.loads(result.stdout)
                return data.get('results', []), errors
            
            if result.stderr:
                errors.append(result.stderr)
                logger.warning(f"Bandit stderr: {result.stderr}")
            
            return [], errors
        
        except subprocess.TimeoutExpired:
            error_msg = "Bandit scan timed out (60s limit)"
            logger.error(error_msg)
            errors.append(error_msg)
            return [], errors
        
        except FileNotFoundError:
            error_msg = "Bandit not found. Install with: pip install bandit"
            logger.error(error_msg)
            errors.append(error_msg)
            return [], errors
        
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse Bandit JSON output: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            return [], errors
        
        except Exception as e:
            error_msg = f"Error running Bandit: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            return [], errors
        
        finally:
            # Clean up temporary file
            if temp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except Exception as e:
                    logger.warning(f"Failed to delete temp file: {e}")

    def _parse_issues(self, raw_issues: List[Dict], filename: str) -> List[SecurityIssue]:
        """Parse raw Bandit issues into SecurityIssue objects."""
        issues = []
        for raw in raw_issues:
            try:
                issue = SecurityIssue(
                    test_id=raw.get('test_id', 'UNKNOWN'),
                    test_name=raw.get('test_name', 'unknown'),
                    severity=raw.get('issue_severity', 'UNDEFINED'),
                    confidence=raw.get('issue_confidence', 'UNDEFINED'),
                    line_number=raw.get('line_number', 0),
                    line_range=raw.get('line_range', []),
                    code=raw.get('code', '').strip(),
                    filename=filename,
                    message=raw.get('issue_text', ''),
                    cwe_id=raw.get('issue_cwe', {}).get('id') if isinstance(raw.get('issue_cwe'), dict) else None,
                    more_info=raw.get('more_info', ''),
                    col_offset=raw.get('col_offset', 0)
                )
                issues.append(issue)
                if issue.is_critical:
                    logger.warning(
                        f"🚨 CRITICAL: {issue.test_id} at line {issue.line_number} "
                        f"- {issue.message}"
                    )
            except Exception as e:
                logger.error(f"Failed to parse issue: {e}")
                continue
        
        return issues
    
    def _calculate_metrics(
        self, 
        issues: List[SecurityIssue], 
        code: str
    ) -> SecurityMetrics:
        """
        Calculate aggregated security metrics.
        """
        metrics = SecurityMetrics()

        metrics.total_lines_scanned = len(code.splitlines())
        metrics.total_issues = len(issues)
        
        # Count by severity
        for issue in issues:
            if issue.severity == Severity.HIGH:
                metrics.high_severity += 1
            elif issue.severity == Severity.MEDIUM:
                metrics.medium_severity += 1
            elif issue.severity == Severity.LOW:
                metrics.low_severity += 1
            else:
                metrics.undefined_severity += 1
        
        # Count by confidence
        for issue in issues:
            if issue.confidence == Confidence.HIGH:
                metrics.high_confidence += 1
            elif issue.confidence == Confidence.MEDIUM:
                metrics.medium_confidence += 1
            elif issue.confidence == Confidence.LOW:
                metrics.low_confidence += 1
            else:
                metrics.undefined_confidence += 1

        # count critical issues
        metrics.critical_issues = sum(1 for i in issues if i.is_critical)

        #count category
        for issue in issues:
            category = issue.get_category()
            metrics.issues_by_category[category] = \
                metrics.issues_by_category.get(category, 0) + 1
        
        #count by test_id
        for issue in issues:
            metrics.issues_by_test[issue.test_id] = \
                metrics.issues_by_test.get(issue.test_id, 0) + 1
        
        return metrics

    def generate_report(
        self, 
        result: SecurityScanResult,
        format: str = "text"
    ) -> str:
        """
        Generate human-readable security report.
        
        Args:
            result: Security scan result
            format: Report format - "text", "markdown", or "json"
        
        Returns:
            Formatted report string
        """
        if format == "json":
            return json.dumps(result.to_dict(), indent=2)
        
        elif format == "markdown":
            return self._generate_markdown_report(result)
        
        else:  # text
            return self._generate_text_report(result)
    
    def _generate_text_report(self, result: SecurityScanResult) -> str:
        """Generate plain text report."""
        lines = []
        lines.append("=" * 70)
        lines.append("SECURITY SCAN REPORT")
        lines.append("=" * 70)
        lines.append(f"Bandit Version: {result.bandit_version}")
        lines.append(f"Scan Time: {result.scan_time:.2f}s")
        lines.append(f"Lines Scanned: {result.metrics.total_lines_scanned}")
        lines.append("")
        
        # Summary
        lines.append("SUMMARY")
        lines.append("-" * 70)
        lines.append(f"Total Issues: {result.metrics.total_issues}")
        lines.append(f"  Critical (High Severity + High Confidence): {result.metrics.critical_issues}")
        lines.append(f"  High Severity: {result.metrics.high_severity}")
        lines.append(f"  Medium Severity: {result.metrics.medium_severity}")
        lines.append(f"  Low Severity: {result.metrics.low_severity}")
        lines.append("")
        
        # Issues by category
        if result.metrics.issues_by_category:
            lines.append("ISSUES BY CATEGORY")
            lines.append("-" * 70)
            for category, count in sorted(
                result.metrics.issues_by_category.items(),
                key=lambda x: x[1],
                reverse=True
            ):
                lines.append(f"  {category}: {count}")
            lines.append("")
        
        # Detailed issues
        if result.has_issues:
            lines.append("DETAILED ISSUES")
            lines.append("-" * 70)
            
            # Sort by priority
            sorted_issues = result.get_sorted_issues(sort_by="priority")
            
            for i, issue in enumerate(sorted_issues, 1):
                lines.append(f"\n{i}. [{issue.severity.value}/{issue.confidence.value}] {issue.test_id}: {issue.test_name}")
                lines.append(f"   Line {issue.line_number} | {issue.get_category()}")
                lines.append(f"   {issue.message}")
                if issue.code:
                    lines.append(f"   Code: {issue.code[:100]}...")
                if issue.more_info:
                    lines.append(f"   More info: {issue.more_info}")
        else:
            lines.append("✅ No security issues found!")
        
        lines.append("")
        lines.append("=" * 70)
        
        return "\n".join(lines)
    
    def _generate_markdown_report(self, result: SecurityScanResult) -> str:
        """Generate Markdown report."""
        lines = []
        lines.append("# Security Scan Report")
        lines.append("")
        lines.append(f"**Bandit Version:** {result.bandit_version}")
        lines.append(f"**Scan Time:** {result.scan_time:.2f}s")
        lines.append(f"**Lines Scanned:** {result.metrics.total_lines_scanned}")
        lines.append("")
        
        # Summary
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- **Total Issues:** {result.metrics.total_issues}")
        lines.append(f"- **Critical Issues:** {result.metrics.critical_issues} 🚨")
        lines.append(f"- **High Severity:** {result.metrics.high_severity}")
        lines.append(f"- **Medium Severity:** {result.metrics.medium_severity}")
        lines.append(f"- **Low Severity:** {result.metrics.low_severity}")
        lines.append("")
        
        # Issues by category
        if result.metrics.issues_by_category:
            lines.append("## Issues by Category")
            lines.append("")
            lines.append("| Category | Count |")
            lines.append("|----------|-------|")
            for category, count in sorted(
                result.metrics.issues_by_category.items(),
                key=lambda x: x[1],
                reverse=True
            ):
                lines.append(f"| {category} | {count} |")
            lines.append("")
        
        # Detailed issues
        if result.has_issues:
            lines.append("## Detailed Issues")
            lines.append("")
            
            sorted_issues = result.get_sorted_issues(sort_by="priority")
            
            for i, issue in enumerate(sorted_issues, 1):
                severity_emoji = {
                    Severity.HIGH: "🔴",
                    Severity.MEDIUM: "🟡",
                    Severity.LOW: "🟢"
                }.get(issue.severity, "⚪")
                
                lines.append(f"### {i}. {severity_emoji} {issue.test_name}")
                lines.append("")
                lines.append(f"- **Test ID:** {issue.test_id}")
                lines.append(f"- **Severity:** {issue.severity.value}")
                lines.append(f"- **Confidence:** {issue.confidence.value}")
                lines.append(f"- **Line:** {issue.line_number}")
                lines.append(f"- **Category:** {issue.get_category()}")
                lines.append("")
                lines.append(f"**Description:** {issue.message}")
                lines.append("")
                if issue.code:
                    lines.append("**Vulnerable Code:**")
                    lines.append("```python")
                    lines.append(issue.code)
                    lines.append("```")
                    lines.append("")
                if issue.more_info:
                    lines.append(f"[More Information]({issue.more_info})")
                    lines.append("")
        else:
            lines.append("✅ **No security issues found!**")
        
        return "\n".join(lines)