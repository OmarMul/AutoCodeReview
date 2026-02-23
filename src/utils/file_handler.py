"""
File handling utilities for GitHub code analysis.
"""

import hashlib
from src.utils.logger import get_logger
from typing import Optional
import chardet

logger = get_logger(__name__)

# Language mapping by extension
LANGUAGE_MAP = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".go": "go",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "hpp",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
}

def read_content(
    content: bytes,
    encoding: Optional[str] = None
) -> str:
    """
    Decode file content with automatic encoding detection.
    Used for content fetched from GitHub API.
    
    Args:
        content: Raw bytes content
        encoding: Force specific encoding (optional)
    
    Returns:
        str: Decoded content
    """
    if not content:
        return ""
    
    # If encoding specified, use it
    if encoding:
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            logger.warning(f"Failed to decode with {encoding}, auto-detecting")
    
    # Try UTF-8 first (most common)
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        pass
    
    # Detect encoding
    detected = chardet.detect(content)
    detected_encoding = detected.get("encoding", "utf-8")
    confidence = detected.get("confidence", 0)
    
    logger.debug(f"Detected encoding: {detected_encoding} (confidence: {confidence:.2f})")
    
    try:
        return content.decode(detected_encoding)
    except (UnicodeDecodeError, TypeError, LookupError):
        # Fallback to latin-1 (never fails)
        logger.warning("Using latin-1 as fallback encoding")
        return content.decode("latin-1")


def detect_language(filename: str) -> str:
    """
    Detect programming language from filename.
    
    Args:
        filename: Filename with extension (e.g., 'main.py')
    
    Returns:
        str: Language name or "unknown"
    """
    # Get extension
    if "." not in filename:
        return "unknown"
    
    extension = "." + filename.split(".")[-1].lower()
    return LANGUAGE_MAP.get(extension, "unknown")


def calculate_hash(content: str) -> str:
    """
    Calculate hash of content for caching.
    
    Args:
        content: File content as string
    
    Returns:
        str: MD5 hash hex string
    """
    content_bytes = content.encode("utf-8")
    return hashlib.md5(content_bytes).hexdigest()