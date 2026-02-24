# """
# Tests for analysis pipeline.
# """

# import pytest
# from src.analyzers.pipeline import AnalysisPipeline, AnalysisStatus


# class TestAnalysisPipeline:
#     """Test analysis pipeline functionality."""
    
#     @pytest.fixture
#     def pipeline(self):
#         """Create pipeline instance."""
#         return AnalysisPipeline(enable_async=False)
    
#     def test_analyze_simple_file(self, pipeline):
#         """Test analyzing a simple file."""
#         code = """
# def hello():
#     '''Say hello.'''
#     print("Hello, World!")

# def add(a, b):
#     return a + b
# """
#         result = pipeline.analyze_file(code, "test.py")
        
#         assert result.filename == "test.py"
#         assert result.total_functions == 2
#         assert result.error is None
#         assert result.analysis_time > 0
    
#     def test_analyze_complex_file(self, pipeline):
#         """Test analyzing file with complexity issues."""
#         code = """
# def complex_function(x):
#     if x > 0:
#         if x > 10:
#             for i in range(x):
#                 if i % 2:
#                     if i > 5:
#                         return i
#     return 0
# """
#         result = pipeline.analyze_file(code, "complex.py")
        
#         assert result.total_functions == 1
#         assert result.max_complexity > 1
        
#         # Function should be flagged as complex
#         complex_funcs = result.get_functions_needing_attention()
#         assert len(complex_funcs) > 0
    
#     def test_analyze_file_with_security_issues(self, pipeline):
#         """Test analyzing file with security vulnerabilities."""
#         code = """
# password = "hardcoded_password"

# def authenticate(user_input):
#     import os
#     os.system(user_input)
# """
#         result = pipeline.analyze_file(code, "vulnerable.py")
        
#         assert result.total_security_issues > 0
        
#         # Check function has security issues
#         func = result.functions[0]
#         assert func.has_security_issues
    
#     def test_analyze_with_changed_lines(self, pipeline):
#         """Test analyzing with changed lines from diff."""
#         code = """
# def func1():
#     pass

# def func2():
#     return 42

# def func3():
#     pass
# """
#         # Only func2 changed (line 5-6)
#         changed_lines = {5, 6}
        
#         result = pipeline.analyze_file(code, "test.py", changed_lines=changed_lines)
        
#         # Check that func2 is marked as changed
#         func2 = next(f for f in result.functions if f.name == "func2")
#         assert func2.is_changed
        
#         # Other functions should not be marked as changed
#         func1 = next(f for f in result.functions if f.name == "func1")
#         assert not func1.is_changed
    
#     def test_analyze_syntax_error(self, pipeline):
#         """Test handling syntax errors."""
#         code = """
# def broken(
#     # Missing closing parenthesis
# """
#         result = pipeline.analyze_file(code, "broken.py")
        
#         assert result.has_errors
#         assert result.error is not None
    
#     def test_analyze_empty_file(self, pipeline):
#         """Test analyzing empty file."""
#         result = pipeline.analyze_file("", "empty.py")
        
#         assert result.total_functions == 0
#         assert result.total_classes == 0
    
#     def test_quality_score_calculation(self, pipeline):
#         """Test quality score calculation."""
#         code = """
# def well_written_function():
#     '''Well documented function.'''
#     x = 1
#     y = 2
#     return x + y
# """
#         result = pipeline.analyze_file(code, "good.py")
        
#         # Should have a good quality score
#         assert result.quality_score > 50
    
#     def test_functions_needing_attention(self, pipeline):
#         """Test identifying functions that need attention."""
#         code = """
# def simple():
#     return 1

# def complex_undocumented(x, y, z):
#     if x > 0:
#         if y > 0:
#             if z > 0:
#                 for i in range(x):
#                     if i % 2:
#                         return i
#     return 0
# """
#         result = pipeline.analyze_file(code, "test.py")
        
#         # complex_undocumented should need attention
#         needs_attention = result.get_functions_needing_attention()
#         assert len(needs_attention) >= 1
#         assert any(f.name == "complex_undocumented" for f in needs_attention)
    
#     def test_progress_callback(self, pipeline):
#         """Test progress tracking."""
#         code = """
# def test():
#     pass
# """
        
#         progress_updates = []
        
#         def callback(progress):
#             progress_updates.append({
#                 'status': progress.status,
#                 'step': progress.current_step,
#                 'percentage': progress.percentage
#             })
        
#         result = pipeline.analyze_file(code, "test.py", progress_callback=callback)
        
#         # Should have received progress updates
#         assert len(progress_updates) > 0
        
#         # Last update should be completed
#         assert progress_updates[-1]['status'] == AnalysisStatus.COMPLETED
    
#     def test_analyse_batch(self, pipeline):
#         """Test analyzing multiple files."""
#         files = [
#             {
#                 'code': "def func1(): pass",
#                 'filename': "file1.py"
#             },
#             {
#                 'code': "def func2(): pass",
#                 'filename': "file2.py"
#             }
#         ]
        
#         result = pipeline.analyse_batch(files)
        
#         assert result.total_files == 2
#         assert len(result.files) == 2
#         assert result.total_analysis_time > 0
    
#     def test_generate_text_report(self, pipeline):
#         """Test text report generation."""
#         code = """
# def test_function():
#     '''Test function.'''
#     return 42
# """
#         analysis = pipeline.analyze_file(code, "test.py")
#         report = pipeline.generate_report(analysis, format="text")
        
#         assert "ANALYSIS REPORT" in report
#         assert "test.py" in report
#         assert "SUMMARY" in report
    
#     def test_generate_markdown_report(self, pipeline):
#         """Test Markdown report generation."""
#         code = """
# def test_function():
#     '''Test function.'''
#     return 42
# """
#         analysis = pipeline.analyze_file(code, "test.py")
#         report = pipeline.generate_report(analysis, format="markdown")
        
#         assert "# Analysis Report" in report
#         assert "## Summary" in report
#         assert "test.py" in report
    
#     def test_file_summary(self, pipeline):
#         """Test file summary generation."""
#         code = """
# def func1():
#     pass

# def func2():
#     return 42
# """
#         analysis = pipeline.analyze_file(code, "test.py")
#         summary = analysis.get_summary()
        
#         assert 'filename' in summary
#         assert 'total_functions' in summary
#         assert 'quality_score' in summary
#         assert 'total_security_issues' in summary


# class TestAnalysisPipelineAsync:
#     """Test async pipeline functionality."""
    
#     @pytest.fixture
#     def async_pipeline(self):
#         """Create async pipeline."""
#         return AnalysisPipeline(enable_async=True)
    
#     def test_analyse_batch_async(self, async_pipeline):
#         """Test async batch analysis."""
#         files = [
#             {'code': f"def func{i}(): pass", 'filename': f"file{i}.py"}
#             for i in range(5)
#         ]
        
#         result = async_pipeline.analyse_batch(files)
        
#         assert result.total_files == 5
#         assert len(result.files) == 5
        
#         # Async should be faster than sequential for multiple files
#         assert result.total_analysis_time > 0


"""
Manual test of analysis pipeline.
"""

from src.analyzers.pipeline import AnalysisPipeline, AnalysisStatus

# Sample code with various issues
sample_code = """
import os
import hashlib

# Hardcoded password - security issue!
PASSWORD = "admin123"

def authenticate(username, password):
    '''Authenticate user - but has SQL injection!'''
    query = "SELECT * FROM users WHERE username='%s'" % username
    return execute_query(query)

def complex_function(x, y, z):
    # No docstring - documentation issue!
    # High complexity - refactoring needed!
    if x > 0:
        if y > 0:
            if z > 0:
                for i in range(x):
                    if i % 2:
                        for j in range(y):
                            if j > 5:
                                if z < 10:
                                    return i + j
    return 0

def run_command(cmd):
    '''Execute system command - command injection!'''
    os.system(cmd)

def simple_function():
    '''A well-written function.'''
    return 42
"""

# Create pipeline
pipeline = AnalysisPipeline()

# Track progress
def progress_callback(progress):
    print(f"[{progress.percentage:.0f}%] {progress.status.value}: {progress.current_step}")

print("=" * 70)
print("ANALYZING CODE")
print("=" * 70)
print()

# Analyze
result = pipeline.analyze_file(
    sample_code,
    "sample.py",
    progress_callback=progress_callback
)

print()
print("=" * 70)
print("ANALYSIS COMPLETE")
print("=" * 70)
print()

# Print summary
summary = result.get_summary()
print("Summary:")
for key, value in summary.items():
    print(f"  {key}: {value}")

print()
print("=" * 70)
print("FUNCTIONS NEEDING ATTENTION")
print("=" * 70)

for func in result.get_functions_needing_attention():
    print(f"\n{func.name} (Line {func.line_start}-{func.line_end})")
    print(f"  Complexity: {func.complexity} ({func.complexity_rank})")
    print(f"  Documented: {'Yes' if func.docstring else 'No'}")
    print(f"  Security Issues: {len(func.security_issues)}")
    print(f"  Issues: {func.get_issues_summary()}")

print()
print("=" * 70)
print("TEXT REPORT")
print("=" * 70)
print()

text_report = pipeline.generate_report(result, format="text")
print(text_report)

print()
print("=" * 70)
print("MARKDOWN REPORT")
print("=" * 70)
print()

md_report = pipeline.generate_report(result, format="markdown")
print(md_report)