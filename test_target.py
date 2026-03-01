
"""
Tests for file_handler utilities.
"""

import pytest
from src.utils.file_handler import read_content, detect_language, calculate_hash


class TestReadContent:
    """Test read_content function."""
    
    def test_read_utf8_content(self):
        """Test reading UTF-8 content."""
        content = b"def hello():\n    print('Hello World')"
        result = read_content(content)
        assert result == "def hello():\n    print('Hello World')"
    
    def test_read_empty_content(self):
        """Test reading empty content."""
        content = b""
        result = read_content(content)
        assert result == ""
    
    def test_read_with_encoding(self):
        """Test reading with specified encoding."""
        content = "Hello World".encode("latin-1")
        result = read_content(content, encoding="latin-1")
        assert result == "Hello World"
    
    def test_read_non_utf8_content(self):
        """Test reading non-UTF-8 content with auto-detection."""
        # Latin-1 specific character
        content = "Café résumé".encode("latin-1")
        result = read_content(content)
        assert "Caf" in result  # Should decode successfully


class TestDetectLanguage:
    """Test detect_language function."""
    
    def test_detect_python(self):
        """Test Python file detection."""
        assert detect_language("main.py") == "python"
        assert detect_language("test.pyi") == "python"
    
    def test_detect_javascript(self):
        """Test JavaScript file detection."""
        assert detect_language("app.js") == "javascript"
        assert detect_language("component.jsx") == "javascript"
        assert detect_language("module.mjs") == "javascript"
    
    def test_detect_typescript(self):
        """Test TypeScript file detection."""
        assert detect_language("app.ts") == "typescript"
        assert detect_language("component.tsx") == "typescript"
    
    def test_detect_java(self):
        """Test Java file detection."""
        assert detect_language("Main.java") == "java"
    
    def test_detect_go(self):
        """Test Go file detection."""
        assert detect_language("main.go") == "go"
    
    def test_detect_cpp(self):
        """Test C++ file detection."""
        assert detect_language("header.hpp") == "hpp"
        assert detect_language("main.cpp") == "cpp"
        
    
    def test_detect_unknown(self):
        """Test unknown file type."""
        assert detect_language("file.xyz") == "unknown"
        assert detect_language("noextension") == "unknown"
    
    def test_case_insensitive(self):
        """Test that detection is case-insensitive."""
        assert detect_language("Main.PY") == "python"
        assert detect_language("App.JS") == "javascript"


class TestCalculateHash:
    """Test calculate_hash function."""
    
    def test_hash_consistency(self):
        """Test that same content produces same hash."""
        content = "def hello(): pass"
        hash1 = calculate_hash(content)
        hash2 = calculate_hash(content)
        assert hash1 == hash2
    
    def test_hash_difference(self):
        """Test that different content produces different hash."""
        content1 = "def hello(): pass"
        content2 = "def goodbye(): pass"
        hash1 = calculate_hash(content1)
        hash2 = calculate_hash(content2)
        assert hash1 != hash2
    
    def test_hash_format(self):
        """Test that hash is hex string of correct length."""
        content = "test content"
        hash_result = calculate_hash(content)
        assert isinstance(hash_result, str)
        assert len(hash_result) == 32  # MD5 produces 32 hex characters
        assert all(c in "0123456789abcdef" for c in hash_result)
    
    def test_empty_content_hash(self):
        """Test hashing empty content."""
        content = ""
        hash_result = calculate_hash(content)
        assert isinstance(hash_result, str)
        assert len(hash_result) == 32