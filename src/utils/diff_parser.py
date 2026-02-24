from typing import List, Dict, Optional, Set
from dataclasses import dataclass
from unidiff import PatchSet
from io import StringIO
from src.utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class ChangedLine:
    """Represents a single line in a diff"""
    line_number: int
    old_line_number: Optional[int]
    content: str
    change_type: str

@dataclass
class ChangedFile:
    """Represents a single file in a diff"""
    filename: str
    old_filename: Optional[str]
    is_new_file: bool
    is_deleted_file: bool
    is_renamed: bool
    is_binary: bool
    added_lines: List[ChangedLine]
    removed_lines: List[ChangedLine]
    modified_lines: List[ChangedLine]
    total_additions: int
    total_deletions: int

    @property
    def changed_line_numbers(self) -> Set[int]:
        """Returns the set of changed line numbers"""
        changed = set()
        for line in self.added_lines + self.modified_lines:
            changed.add(line.line_number)
        return changed

    @property
    def get_context_lines(self, line_number: int, context_lines: int = 3) -> tuple:
        """Get line range around a changed line for context"""
        start = max(1, line_number - context_lines)
        end = line_number + context_lines
        return (start, end)


@dataclass
class DiffResult:
    """Complete Diff parasing result"""
    files: List[ChangedFile]
    total_files_changed: int
    total_additions: int
    total_deletions: int

    @property
    def get_python_files(self) -> List[ChangedFile]:
        """Get only python files"""
        return [file for file in self.files if file.filename.endswith(".py")]

    @property
    def get_file_by_name(self, filename: str) -> Optional[ChangedFile]:
            """Get a file by name"""
            for file in self.files:
                if file.filename == filename:
                    return file
            return None

class DiffParser:
    """Parser for git diff format"""
    
    def parse_diff(self, diff_text: str) -> DiffResult:
        """Parse git diff text"""
        
        if not diff_text or not diff_text.strip():
            logger.warning("Empty diff text provided")
            return DiffResult(
                files=[],
                total_files_changed=0,
                total_additions=0,
                total_deletions=0
            )
        
        try:
            # parse using unidiff
            patch_set = PatchSet(StringIO(diff_text))
            files =[]
            total_additions = 0
            total_deletions = 0

            for patched_file in patch_set:
                file = self._parse_file(patched_file)
                files.append(file)
                total_additions += file.total_additions
                total_deletions += file.total_deletions


            logger.info(f"parsed diff: {len(files)} files, "
            f"+{total_additions} - {total_deletions} lines")

            return DiffResult(
                files=files,
                total_files_changed=len(files),
                total_additions=total_additions,
                total_deletions=total_deletions
            )

        except Exception as e:
            logger.error(f"Error parsing diff: {e}")
            raise


    def _parse_file(self, patched_file) -> ChangedFile:
        """Parse a single file from unidiff"""
        
        source_file = patched_file.source_file
        target_file = patched_file.target_file

        # Remove 'a/' and 'b/' prefixes from git diff
        if source_file.startswith('a/'):
            source_file = source_file[2:]
        if target_file.startswith('b/'):
            target_file = target_file[2:]

        # Detect file type
        is_new_file = patched_file.is_added_file
        is_deleted_file = patched_file.is_removed_file
        is_renamed = patched_file.is_rename
        is_binary = patched_file.is_binary_file

        filename = target_file
        old_filename = source_file if is_renamed else None
        
        added_lines = []
        removed_lines = []
        modified_lines = []
        total_additions = 0
        total_deletions = 0

        # dont process binary files
        if is_binary:
            logger.info(f"Skipping binary file: {filename}")
            return ChangedFile(
                filename=filename,
                old_filename=old_filename,
                is_new_file=is_new_file,
                is_deleted_file=is_deleted_file,
                is_renamed=is_renamed,
                is_binary=is_binary,
                added_lines=[],
                removed_lines=[],
                modified_lines=[],
                total_additions=0,
                total_deletions=0
            )
        
        #process huncks
        for hunk in patched_file:
            for line in hunk:
                if line.is_added:
                    changed_line = ChangedLine(
                        line_number=line.target_line_no,
                        old_line_number=None,
                        content=line.value.rstrip('\n'),
                        change_type="added"
                    )
                    added_lines.append(changed_line)
                    total_additions += 1
                elif line.is_removed:
                    changed_line = ChangedLine(
                        line_number=line.source_line_no,
                        old_line_number=line.source_line_no,
                        content=line.value.rstrip('\n'),
                        change_type="removed"
                    )
                    removed_lines.append(changed_line)
                    total_deletions += 1
        modified_lines = self._detect_modified_lines(removed_lines, added_lines)
        return ChangedFile(
            filename=filename,
            old_filename=old_filename,
            is_new_file=is_new_file,
            is_deleted_file=is_deleted_file,
            is_renamed=is_renamed,
            is_binary=is_binary,
            added_lines=added_lines,
            removed_lines=removed_lines,
            modified_lines=modified_lines,
            total_additions=total_additions,
            total_deletions=total_deletions
        )

    def _detect_modified_lines(self, removed_lines: List[ChangedLine], added_lines: List[ChangedLine]) -> List[ChangedLine]:
        """Detect modified lines from removed and added lines"""
        modified = []
        
        #TODO: implement modified lines detection
        
        return modified

    def parse_github_pr_diff(self, pr_diff: str) -> DiffResult:
        """Parse diff from GitHub PR API.
        GitHub provides diffs in unified format."""
        
        return self.parse_diff(pr_diff)

    def get_changed_functions(
        self,
        file_change: ChangedFile,
        parse_result
    ) -> List[str]:
        """
        Get list of function names that have changes.
        """
        changed_line_numbers = file_change.changed_line_numbers()
        changed_functions = []
        
        # Check which functions contain changed lines
        for func in parse_result.functions:
            # Check if any changed line is within function range
            for line_num in changed_line_numbers:
                if func.line_start <= line_num <= func.line_end:
                    if func.name not in changed_functions:
                        changed_functions.append(func.name)
                    break
        
        return changed_functions