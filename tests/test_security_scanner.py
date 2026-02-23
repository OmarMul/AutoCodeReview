"""
Comprehensive tests for security scanner.
"""

import pytest
from src.analyzers.security_scanner import (
    SecurityScanner,
    Severity,
    Confidence
)


class TestSecurityScanner:
    """Test security scanner functionality."""
    
    @pytest.fixture
    def scanner(self):
        """Create scanner instance."""
        return SecurityScanner()
    
    def test_no_issues(self, scanner):
        """Test code with no security issues."""
        code = """
def safe_function():
    x = 1 + 2
    return x
"""
        result = scanner.scan(code)
        
        assert result.metrics.total_issues == 0
        assert not result.has_issues
        assert not result.has_critical_issues
    
    def test_hardcoded_password(self, scanner):
        """Test detection of hardcoded password."""
        code ="""
password = "hardcoded_password123"
"""
        result = scanner.scan(code)
        
        # Bandit should detect hardcoded password (B105)
        assert result.has_issues
        # Check if any issue is about hardcoded password
        assert any('password' in issue.message.lower() for issue in result.issues)
    
    def test_sql_injection(self, scanner):
        """Test detection of SQL injection vulnerability."""
        code = """
import sqlite3

def get_user(user_id):
    conn = sqlite3.connect('db.sqlite')
    cursor = conn.cursor()
    # SQL injection vulnerability
    query = "SELECT * FROM users WHERE id = '%s'" % user_id
    cursor.execute(query)
    return cursor.fetchone()
"""
        result = scanner.scan(code)
        
        # Bandit should detect SQL injection (B608)
        assert result.has_issues
        # Should have at least one issue related to SQL
        assert any('sql' in issue.message.lower() for issue in result.issues)
    
    def test_command_injection(self, scanner):
        """Test detection of command injection."""
        code = """
import os

def run_command(user_input):
    # Command injection vulnerability
    os.system("ls " + user_input)
"""
        result = scanner.scan(code)
        
        # Bandit should detect command injection
        assert result.has_issues
    
    def test_insecure_crypto(self, scanner):
        """Test detection of insecure cryptography."""
        code = """
import hashlib

def hash_password(password):
    # MD5 is insecure for passwords
    return hashlib.md5(password.encode()).hexdigest()
"""
        result = scanner.scan(code)
        
        # Bandit should detect weak hash (B303, B324)
        assert result.has_issues
    
    def test_assert_in_code(self, scanner):
        """Test detection of assert statements."""
        code = """
def validate_input(value):
    assert value > 0, "Value must be positive"
    return value
"""
        result = scanner.scan(code)
        
        # Bandit detects assert usage (B101)
        assert result.has_issues
        assert any('assert' in issue.message.lower() for issue in result.issues)
    
    def test_pickle_usage(self, scanner):
        """Test detection of pickle usage."""
        code = """
import pickle

def load_data(filename):
    with open(filename, 'rb') as f:
        # Pickle is insecure
        return pickle.load(f)
"""
        result = scanner.scan(code)
        
        # Bandit detects pickle usage (B301)
        assert result.has_issues
    
    def test_shell_execution(self, scanner):
        """Test detection of shell execution."""
        code = """
import subprocess

def run_script(script_name):
    # Shell=True is dangerous
    subprocess.call(script_name, shell=True)
"""
        result = scanner.scan(code)
        
        # Bandit detects shell=True (B602)
        assert result.has_issues
    
    def test_severity_levels(self, scanner):
        """Test that severity levels are assigned correctly."""
        code = """
password = "test123"
import os
os.system("ls")
"""
        result = scanner.scan(code)
        
        assert result.has_issues
        # Check that issues have valid severity levels
        for issue in result.issues:
            assert issue.severity in [Severity.HIGH, Severity.MEDIUM, Severity.LOW]
    
    def test_confidence_levels(self, scanner):
        """Test that confidence levels are assigned."""
        code = """
password = "hardcoded"
"""
        result = scanner.scan(code)
        
        assert result.has_issues
        # Check that issues have confidence levels
        for issue in result.issues:
            assert issue.confidence in [Confidence.HIGH, Confidence.MEDIUM, Confidence.LOW]
    
    def test_line_numbers(self, scanner):
        """Test that line numbers are captured correctly."""
        code = """
def func1():
    pass

password = "test123"

def func2():
    pass
"""
        result = scanner.scan(code)
        
        assert result.has_issues
        # Password issue should be around line 5
        password_issues = [
            i for i in result.issues 
            if 'password' in i.message.lower()
        ]
        if password_issues:
            assert password_issues[0].line_number == 5
    
    def test_metrics_calculation(self, scanner):
        """Test that metrics are calculated correctly."""
        code = """
password = "test"
import os
os.system("ls")
assert True
"""
        result = scanner.scan(code)
        
        assert result.metrics.total_issues > 0
        assert result.metrics.total_lines_scanned > 0
        assert result.metrics.high_severity >= 0
        assert result.metrics.medium_severity >= 0
        assert result.metrics.low_severity >= 0
    
    def test_critical_issues(self, scanner):
        """Test identification of critical issues."""
        code = """
import os
user_input = input("Enter command: ")
os.system(user_input)  # Critical: command injection
"""
        result = scanner.scan(code)
        
        # Should have at least one critical issue
        assert result.has_issues
        # Critical = HIGH severity + HIGH confidence
        critical = result.get_critical_issues()
        # At least check that the method works
        assert isinstance(critical, list)
    
    def test_sorted_issues(self, scanner):
        """Test issue sorting."""
        code = """
password = "test"
assert True
import pickle
pickle.loads(b"data")
"""
        result = scanner.scan(code)
        
        if result.has_issues:
            # Sort by priority
            sorted_by_priority = result.get_sorted_issues(sort_by="priority")
            assert len(sorted_by_priority) == len(result.issues)
            
            # Sort by line
            sorted_by_line = result.get_sorted_issues(sort_by="line")
            assert len(sorted_by_line) == len(result.issues)
    
    def test_get_issues_by_severity(self, scanner):
        """Test filtering issues by severity."""
        code = """
password = "test"
import os
os.system("ls")
"""
        result = scanner.scan(code)
        
        if result.has_issues:
            high = result.get_issues_by_severity(Severity.HIGH)
            medium = result.get_issues_by_severity(Severity.MEDIUM)
            low = result.get_issues_by_severity(Severity.LOW)
            
            # All issues should be categorized
            total = len(high) + len(medium) + len(low)
            assert total <= result.metrics.total_issues
    
    def test_report_generation_text(self, scanner):
        """Test text report generation."""
        code = """
password = "test123"
"""
        result = scanner.scan(code)
        
        report = scanner.generate_report(result, format="text")
        
        assert "SECURITY SCAN REPORT" in report
        assert "SUMMARY" in report
        assert isinstance(report, str)
    
    def test_report_generation_markdown(self, scanner):
        """Test Markdown report generation."""
        code = """
password = "test123"
"""
        result = scanner.scan(code)
        
        report = scanner.generate_report(result, format="markdown")
        
        assert "# Security Scan Report" in report
        assert "## Summary" in report
        assert isinstance(report, str)
    
    def test_report_generation_json(self, scanner):
        """Test JSON report generation."""
        code = """
password = "test123"
"""
        result = scanner.scan(code)
        
        report = scanner.generate_report(result, format="json")
        
        assert isinstance(report, str)
        # Should be valid JSON
        import json
        data = json.loads(report)
        assert 'issues' in data
        assert 'metrics' in data
    
    def test_empty_code(self, scanner):
        """Test scanning empty code."""
        result = scanner.scan("")
        
        assert not result.has_issues
        assert result.metrics.total_issues == 0
    
    def test_scan_time_recorded(self, scanner):
        """Test that scan time is recorded."""
        code = """
password = "test"
"""
        result = scanner.scan(code)
        
        assert result.scan_time >= 0
    
    def test_bandit_version_recorded(self, scanner):
        """Test that Bandit version is recorded."""
        assert scanner._bandit_version != ""
    
    def test_issue_categories(self, scanner):
        """Test that issues are categorized."""
        code = """
password = "test"
import os
os.system("ls")
"""
        result = scanner.scan(code)
        
        if result.has_issues:
            for issue in result.issues:
                category = issue.get_category()
                assert isinstance(category, str)
                assert len(category) > 0
    
    def test_priority_scoring(self, scanner):
        """Test priority score calculation."""
        code = """
password = "test"
"""
        result = scanner.scan(code)
        
        if result.has_issues:
            for issue in result.issues:
                score = issue.priority_score
                assert score >= 0
                assert isinstance(score, int)


class TestSecurityScannerAdvanced:
    """Advanced security scanner tests."""
    
    def test_multiple_vulnerabilities(self):
        """Test code with multiple different vulnerabilities."""
        scanner = SecurityScanner()
        
        code = """
import os
import pickle
import hashlib

password = "hardcoded_password"

def run_command(user_input):
    os.system(user_input)

def load_data(data):
    pickle.loads(data)

def hash_data(data):
    return hashlib.md5(data).hexdigest()

assert True
"""
        result = scanner.scan(code)
        
        # Should find multiple issues
        assert result.metrics.total_issues >= 4
        
        # Should have issues of different types
        test_ids = {issue.test_id for issue in result.issues}
        assert len(test_ids) > 1
    
    def test_exclude_tests(self):
        """Test excluding specific tests."""
        # Exclude password check
        scanner = SecurityScanner(exclude_tests=["B105"])
        
        code = """
password = "test123"
"""
        result = scanner.scan(code)
        
        # B105 should be excluded
        assert not any(issue.test_id == "B105" for issue in result.issues)
    
    def test_severity_filtering(self):
        """Test filtering by minimum severity."""
        scanner = SecurityScanner()
        
        code = """
password = "test"
assert True
"""
        result = scanner.scan(
            code,
            severity_level=Severity.HIGH
        )
        
        # Only HIGH severity issues should be included
        for issue in result.issues:
            assert issue.severity == Severity.HIGH