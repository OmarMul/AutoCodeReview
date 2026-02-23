"""
Tests for diff parser.
"""

import pytest
from src.utils.diff_parser import DiffParser


class TestDiffParser:
    """Test diff parsing functionality."""
    
    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return DiffParser()
    
    def test_parse_simple_addition(self, parser):
        """Test parsing a simple line addition."""
        diff = """
diff --git a/test.py b/test.py
index 1234567..abcdefg 100644
--- a/test.py
+++ b/test.py
@@ -1,3 +1,4 @@
 def hello():
+    print("Hello")
     pass
"""
        result = parser.parse_diff(diff)
        
        assert result.total_files_changed == 1
        assert result.total_additions == 1
        assert result.total_deletions == 0
        
        file_change = result.files[0]
        assert file_change.filename == "test.py"
        assert len(file_change.added_lines) == 1
        assert file_change.added_lines[0].line_number == 2
        assert 'print("Hello")' in file_change.added_lines[0].content
    
    def test_parse_deletion(self, parser):
        """Test parsing line deletion."""
        diff = """
diff --git a/test.py b/test.py
index 1234567..abcdefg 100644
--- a/test.py
+++ b/test.py
@@ -1,4 +1,3 @@
 def hello():
-    print("Old")
     pass
"""
        result = parser.parse_diff(diff)
        
        assert result.total_additions == 0
        assert result.total_deletions == 1
        
        file_change = result.files[0]
        assert len(file_change.removed_lines) == 1
        assert 'print("Old")' in file_change.removed_lines[0].content
    
    def test_parse_multiple_files(self, parser):
        """Test parsing changes to multiple files."""
        diff = """
diff --git a/file1.py b/file1.py
index 1111111..2222222 100644
--- a/file1.py
+++ b/file1.py
@@ -1,2 +1,3 @@
 line1
+line2
 line3
diff --git a/file2.py b/file2.py
index 3333333..4444444 100644
--- a/file2.py
+++ b/file2.py
@@ -1,2 +1,2 @@
-old line
+new line
 line2
"""
        result = parser.parse_diff(diff)
        
        assert result.total_files_changed == 2
        assert result.files[0].filename == "file1.py"
        assert result.files[1].filename == "file2.py"
    
    def test_parse_new_file(self, parser):
        """Test parsing a newly added file."""
        diff = """
diff --git a/new_file.py b/new_file.py
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/new_file.py
@@ -0,0 +1,3 @@
+def new_function():
+    pass
+
"""
        result = parser.parse_diff(diff)
        
        file_change = result.files[0]
        assert file_change.is_new_file is True
        assert file_change.filename == "new_file.py"
        assert len(file_change.added_lines) == 3
    
    def test_parse_deleted_file(self, parser):
        """Test parsing a deleted file."""
        diff = """
diff --git a/deleted.py b/deleted.py
deleted file mode 100644
index 1234567..0000000
--- a/deleted.py
+++ /dev/null
@@ -1,3 +0,0 @@
-def old_function():
-    pass
-
"""
        result = parser.parse_diff(diff)
        
        file_change = result.files[0]
        assert file_change.is_deleted_file is True
    
    def test_parse_renamed_file(self, parser):
        """Test parsing a renamed file."""
        diff = """
diff --git a/old_name.py b/new_name.py
similarity index 100%
rename from old_name.py
rename to new_name.py
"""
        result = parser.parse_diff(diff)
        
        file_change = result.files[0]
        assert file_change.is_renamed is True
        assert file_change.filename == "new_name.py"
        assert file_change.old_filename == "old_name.py"
    
    def test_get_changed_line_numbers(self, parser):
        """Test getting set of changed line numbers."""
        diff = """
diff --git a/test.py b/test.py
index 1234567..abcdefg 100644
--- a/test.py
+++ b/test.py
@@ -1,5 +1,6 @@
 line1
 line2
+new line at 3
 line3
 line4
+new line at 5
"""
        result = parser.parse_diff(diff)
        file_change = result.files[0]
        
        changed_lines = file_change.get_changed_line_numbers()
        assert 3 in changed_lines
        assert 5 in changed_lines  # Note: this might be 6 after insertion
    
    def test_get_context_range(self, parser):
        """Test getting context around a changed line."""
        diff = """
diff --git a/test.py b/test.py
index 1234567..abcdefg 100644
--- a/test.py
+++ b/test.py
@@ -5,3 +5,4 @@
 line5
 line6
+changed at line 7
"""
        result = parser.parse_diff(diff)
        file_change = result.files[0]
        
        # Get context around line 7 (3 lines before and after)
        start, end = file_change.get_context_range(7, context_size=3)
        assert start == 4  # 7 - 3
        assert end == 10   # 7 + 3
    
    def test_filter_python_files(self, parser):
        """Test filtering only Python files."""
        diff = """
diff --git a/script.py b/script.py
index 1234567..abcdefg 100644
--- a/script.py
+++ b/script.py
@@ -1,2 +1,3 @@
 line1
+line2
diff --git a/readme.md b/readme.md
index 1234567..abcdefg 100644
--- a/readme.md
+++ b/readme.md
@@ -1,2 +1,3 @@
 # Title
+New line
"""
        result = parser.parse_diff(diff)
        
        python_files = result.get_python_files()
        assert len(python_files) == 1
        assert python_files[0].filename == "script.py"
    
    def test_empty_diff(self, parser):
        """Test parsing empty diff."""
        result = parser.parse_diff("")
        
        assert result.total_files_changed == 0
        assert len(result.files) == 0
    
    def test_binary_file(self, parser):
        """Test handling binary files."""
        diff = """
diff --git a/image.png b/image.png
index 1234567..abcdefg 100644
Binary files a/image.png and b/image.png differ
"""
        result = parser.parse_diff(diff)
        
        file_change = result.files[0]
        assert file_change.is_binary is True
        assert len(file_change.added_lines) == 0
        assert len(file_change.removed_lines) == 0