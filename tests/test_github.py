import pytest
from unittest.mock import Mock, patch

from src.github.client import GithubClient
from src.github.pr_handler import PRHandler
from src.github.comment_formatter import CommentFormatter


@pytest.fixture
def mock_github_client():
    with patch('src.github.client.Github') as mock_github:
        # Prevent default initialization call from trying to fetch real data
        client = GithubClient(token="fake_token")
        yield client


class TestGithubClient:
    def test_init_with_token(self):
        with patch('src.github.client.Github') as mock_gh:
            client = GithubClient(token="test_token")
            mock_gh.assert_called_once_with("test_token")
            
    def test_init_without_token(self):
        with patch('os.environ.get', return_value="env_token"), \
             patch('src.github.client.Github') as mock_gh:
            client = GithubClient()
            mock_gh.assert_called_once_with("env_token")

    def test_get_file_content(self):
        with patch('src.github.client.Github'):
            client = GithubClient(token="test_token")
            
            mock_repo = Mock()
            mock_content = Mock()
            mock_content.decoded_content = b"print('Hello World')"
            mock_repo.get_contents.return_value = mock_content
            
            client.get_repo = Mock(return_value=mock_repo)
            client.check_rate_limit = Mock()
            
            content = client.get_file_content("owner/repo", "main.py", "main")
            
            assert content == "print('Hello World')"
            mock_repo.get_contents.assert_called_once_with("main.py", ref="main")

    def test_post_pr_comment(self):
        with patch('src.github.client.Github'):
            client = GithubClient(token="test_token")
            
            mock_repo = Mock()
            mock_pr = Mock()
            mock_repo.get_pull.return_value = mock_pr
            
            client.get_repo = Mock(return_value=mock_repo)
            client.check_rate_limit = Mock()
            
            client.post_pr_comment("owner/repo", 123, "Test Comment")
            
            mock_repo.get_pull.assert_called_once_with(123)
            mock_pr.create_issue_comment.assert_called_once_with("Test Comment")


class TestPRHandler:
    @pytest.fixture
    def pr_handler(self, mock_github_client):
        return PRHandler(mock_github_client)
        
    def test_get_pr_details(self, pr_handler):
        # Mock repo and PR
        mock_repo = Mock()
        mock_pr = Mock()
        mock_pr.number = 123
        mock_pr.title = "Test PR"
        mock_pr.body = "This is a test PR"
        mock_pr.state = "open"
        mock_pr.user.login = "testuser"
        mock_pr.base.ref = "main"
        mock_pr.head.ref = "feature"
        
        mock_repo.get_pull.return_value = mock_pr
        pr_handler.client.client.get_repo.return_value = mock_repo
        
        details = pr_handler.get_pr_details("owner/repo", 123)
        
        assert details["number"] == 123
        assert details["title"] == "Test PR"
        assert details["author"] == "testuser"
        assert details["state"] == "open"
        
    def test_get_changed_files(self, pr_handler):
        mock_repo = Mock()
        mock_pr = Mock()
        
        mock_file1 = Mock()
        mock_file1.filename = "src/main.py"
        mock_file2 = Mock()
        mock_file2.filename = "tests/test_main.py"
        
        mock_pr.get_files.return_value = [mock_file1, mock_file2]
        mock_repo.get_pull.return_value = mock_pr
        pr_handler.client.client.get_repo.return_value = mock_repo
        
        files = pr_handler.get_changed_files("owner/repo", 123)
        
        assert len(files) == 2
        assert "src/main.py" in files
        assert "tests/test_main.py" in files


class TestCommentFormatter:
    def test_format_empty_reviews(self):
        result = CommentFormatter.format_review_comment([])
        assert "No issues found" in result
        assert "✅" in result
        
    def test_format_with_reviews(self):
        reviews = [
            {
                "file": "src/main.py",
                "line": 10,
                "severity": "CRITICAL",
                "feedback": "Syntax error potential here.",
                "suggestion": "Fix the syntax."
            },
            {
                "file": "src/main.py",
                "line": 15,
                "severity": "COMMENT",
                "feedback": "Nice job on this."
            }
        ]
        
        result = CommentFormatter.format_review_comment(reviews)
        
        assert "## 🤖 AutoCodeReview Feedback" in result
        assert "### 📄 `src/main.py`" in result
        assert "🚨 **[CRITICAL]** (Line 10): Syntax error potential here." in result
        assert "```python\nFix the syntax.\n```" in result
        assert "ℹ️ **[COMMENT]** (Line 15): Nice job on this." in result
