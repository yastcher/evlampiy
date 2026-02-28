import json
from unittest.mock import AsyncMock, patch

from src.categorization import (
    categorize_all_income,
    categorize_note,
    classify_note,
    get_existing_categories,
    get_vocabulary_from_repo,
    move_github_file,
    update_vocabulary_in_repo,
)
from src.github_api import GitHubRepo

_TEST_REPO = GitHubRepo(token="token", owner="owner", repo="repo")


class TestGetExistingCategories:
    """Test category listing from GitHub repo."""

    async def test_filters_excluded_categories(self):
        """income and trash folders are excluded from categories."""
        mock_contents = [
            {"name": "income", "type": "dir"},
            {"name": "trash", "type": "dir"},
            {"name": "work", "type": "dir"},
            {"name": "personal", "type": "dir"},
            {"name": "README.md", "type": "file"},
        ]

        with patch("src.categorization.get_repo_contents", AsyncMock(return_value=mock_contents)):
            result = await get_existing_categories(_TEST_REPO)

        assert "income" not in result
        assert "trash" not in result
        assert "work" in result
        assert "personal" in result
        assert len(result) == 2

    async def test_returns_empty_list_on_empty_repo(self):
        """Returns empty list when no categories exist."""
        with patch("src.categorization.get_repo_contents", AsyncMock(return_value=[])):
            result = await get_existing_categories(_TEST_REPO)

        assert result == []


class TestGetVocabularyFromRepo:
    """Test vocabulary.json loading from GitHub repo."""

    async def test_returns_parsed_json(self):
        """Returns vocabulary dict when file exists and is valid JSON."""
        vocab = {"work": ["project", "deadline"], "sports": ["training"]}
        with patch(
            "src.categorization.get_github_file",
            AsyncMock(return_value=(json.dumps(vocab), "sha123")),
        ):
            result = await get_vocabulary_from_repo(_TEST_REPO)
        assert result == vocab

    async def test_returns_empty_dict_when_file_missing(self):
        """Returns {} when vocabulary.json does not exist."""
        with patch("src.categorization.get_github_file", AsyncMock(return_value=None)):
            result = await get_vocabulary_from_repo(_TEST_REPO)
        assert result == {}

    async def test_returns_empty_dict_on_invalid_json(self):
        """Returns {} when vocabulary.json is not valid JSON."""
        with patch(
            "src.categorization.get_github_file",
            AsyncMock(return_value=("not valid json {{{", "sha123")),
        ):
            result = await get_vocabulary_from_repo(_TEST_REPO)
        assert result == {}


class TestUpdateVocabularyInRepo:
    """Test vocabulary.json update in GitHub repo."""

    async def test_merges_new_keywords(self):
        """New keywords are merged with existing ones."""
        existing = {"work": ["project"]}
        put_calls = []

        async def fake_put(repo_info, path, content, commit_message):
            put_calls.append(json.loads(content))
            return True

        with (
            patch(
                "src.categorization.get_github_file",
                AsyncMock(return_value=(json.dumps(existing), "sha")),
            ),
            patch("src.categorization.put_github_file", side_effect=fake_put),
        ):
            await update_vocabulary_in_repo(_TEST_REPO, "work", ["deadline"])

        assert len(put_calls) == 1
        assert "project" in put_calls[0]["work"]
        assert "deadline" in put_calls[0]["work"]

    async def test_deduplicates_keywords(self):
        """Duplicate keywords are removed."""
        existing = {"work": ["project", "deadline"]}
        put_calls = []

        async def fake_put(repo_info, path, content, commit_message):
            put_calls.append(json.loads(content))
            return True

        with (
            patch(
                "src.categorization.get_github_file",
                AsyncMock(return_value=(json.dumps(existing), "sha")),
            ),
            patch("src.categorization.put_github_file", side_effect=fake_put),
        ):
            await update_vocabulary_in_repo(_TEST_REPO, "work", ["project", "sprint"])

        assert put_calls[0]["work"].count("project") == 1
        assert "sprint" in put_calls[0]["work"]

    async def test_caps_at_50_keywords(self):
        """Keywords are capped at 50 per category."""
        existing_keywords = [f"word{i}" for i in range(48)]
        existing = {"work": existing_keywords}
        put_calls = []

        async def fake_put(repo_info, path, content, commit_message):
            put_calls.append(json.loads(content))
            return True

        with (
            patch(
                "src.categorization.get_github_file",
                AsyncMock(return_value=(json.dumps(existing), "sha")),
            ),
            patch("src.categorization.put_github_file", side_effect=fake_put),
        ):
            await update_vocabulary_in_repo(_TEST_REPO, "work", ["new1", "new2", "new3", "new4"])

        assert len(put_calls[0]["work"]) == 50

    async def test_creates_new_category_entry(self):
        """Creates new vocabulary entry when category doesn't exist yet."""
        put_calls = []

        async def fake_put(repo_info, path, content, commit_message):
            put_calls.append(json.loads(content))
            return True

        with (
            patch("src.categorization.get_github_file", AsyncMock(return_value=None)),
            patch("src.categorization.put_github_file", side_effect=fake_put),
        ):
            await update_vocabulary_in_repo(_TEST_REPO, "new_category", ["word1", "word2"])

        assert "new_category" in put_calls[0]
        assert put_calls[0]["new_category"] == ["word1", "word2"]


class TestClassifyNote:
    """Test note classification via AI provider."""

    async def test_returns_existing_category_and_keywords(self):
        """Returns (category, keywords) tuple from JSON response."""
        response = json.dumps({"category": "work", "keywords": ["project", "meeting"]})
        with patch("src.categorization.classify_text", AsyncMock(return_value=response)):
            category, keywords = await classify_note(
                "Meeting notes about project X", ["work", "personal"]
            )

        assert category == "work"
        assert keywords == ["project", "meeting"]

    async def test_suggests_new_category(self):
        """Suggests new category name when no existing match."""
        response = json.dumps({"category": "health_fitness", "keywords": ["gym", "workout"]})
        with patch("src.categorization.classify_text", AsyncMock(return_value=response)):
            category, keywords = await classify_note("Gym workout plan", ["work", "personal"])

        assert category == "health_fitness"
        assert "gym" in keywords

    async def test_returns_none_tuple_on_ai_failure(self):
        """Returns (None, []) when AI provider returns None."""
        with patch("src.categorization.classify_text", AsyncMock(return_value=None)):
            category, keywords = await classify_note("Some text", ["work"])

        assert category is None
        assert keywords == []

    async def test_normalizes_category_name(self):
        """Converts spaces to underscores and lowercases category from JSON."""
        response = json.dumps({"category": "Health Fitness", "keywords": []})
        with patch("src.categorization.classify_text", AsyncMock(return_value=response)):
            category, _keywords = await classify_note("Workout notes", [])

        assert category == "health_fitness"

    async def test_fallback_on_plain_text_response(self):
        """Falls back to plain text parsing when LLM returns non-JSON."""
        with patch("src.categorization.classify_text", AsyncMock(return_value="work")):
            category, keywords = await classify_note("Meeting notes", ["work"])

        assert category == "work"
        assert keywords == []

    async def test_vocabulary_hint_included_in_prompt(self):
        """Vocabulary keywords are included in the prompt sent to the AI."""
        vocabulary = {"sports": ["спорт", "тренировка"]}
        captured = []

        async def capture_prompt(prompt):
            captured.append(prompt)
            return json.dumps({"category": "sports", "keywords": []})

        with patch("src.categorization.classify_text", side_effect=capture_prompt):
            await classify_note("Training session", ["sports"], vocabulary=vocabulary)

        assert len(captured) == 1
        assert "спорт" in captured[0]
        assert "тренировка" in captured[0]

    async def test_keywords_capped_at_5(self):
        """Only the first 5 keywords from LLM response are kept."""
        response = json.dumps({"category": "work", "keywords": ["a", "b", "c", "d", "e", "f", "g"]})
        with patch("src.categorization.classify_text", AsyncMock(return_value=response)):
            _, keywords = await classify_note("Some note", [])

        assert len(keywords) == 5


class TestMoveGithubFile:
    """Test file move operation in GitHub."""

    async def test_moves_file_successfully(self):
        """File is moved by copying and deleting."""
        with (
            patch(
                "src.categorization.get_github_file",
                AsyncMock(return_value=("content", "sha123")),
            ),
            patch("src.categorization.put_github_file", AsyncMock(return_value=True)),
            patch("src.categorization.delete_github_file", AsyncMock(return_value=True)),
        ):
            result = await move_github_file(_TEST_REPO, "income/note.md", "work/note.md")

        assert result is True

    async def test_returns_false_when_file_not_found(self):
        """Returns False when source file doesn't exist."""
        with patch("src.categorization.get_github_file", AsyncMock(return_value=None)):
            result = await move_github_file(_TEST_REPO, "income/note.md", "work/note.md")

        assert result is False

    async def test_returns_false_when_copy_fails(self):
        """Returns False when put_github_file fails."""
        with (
            patch(
                "src.categorization.get_github_file",
                AsyncMock(return_value=("content", "sha123")),
            ),
            patch("src.categorization.put_github_file", AsyncMock(return_value=False)),
        ):
            result = await move_github_file(_TEST_REPO, "income/note.md", "work/note.md")

        assert result is False


class TestCategorizeNote:
    """Trophy integration: mock at external boundary (GitHub HTTP + AI), let internals flow."""

    async def test_categorizes_and_moves_note(self):
        """Full pipeline: categories → vocabulary → classify → move → update vocab."""
        vocab = {"work": ["project"]}

        async def fake_get_repo_contents(repo_info, path=""):
            return [
                {"name": "income", "type": "dir"},
                {"name": "work", "type": "dir"},
                {"name": "personal", "type": "dir"},
            ]

        async def fake_get_github_file(repo_info, path):
            if path == "vocabulary.json":
                return (json.dumps(vocab), "sha_vocab")
            if path.startswith("income/"):
                return ("Meeting notes about project X", "sha_note")
            return None

        put_calls = []

        async def fake_put(repo_info, path, content, commit_message):
            put_calls.append({"path": path, "content": content})
            return True

        with (
            patch("src.categorization.get_repo_contents", side_effect=fake_get_repo_contents),
            patch("src.categorization.get_github_file", side_effect=fake_get_github_file),
            patch("src.categorization.put_github_file", side_effect=fake_put),
            patch("src.categorization.delete_github_file", AsyncMock(return_value=True)),
            patch(
                "src.categorization.classify_text",
                AsyncMock(
                    return_value=json.dumps(
                        {"category": "work", "keywords": ["meeting", "project"]}
                    )
                ),
            ),
        ):
            result = await categorize_note(_TEST_REPO, "note.md", "Meeting notes")

        assert result == "work"
        # File was moved to work/note.md
        assert any(c["path"] == "work/note.md" for c in put_calls)
        # Vocabulary was updated with merged keywords
        vocab_puts = [c for c in put_calls if c["path"] == "vocabulary.json"]
        assert len(vocab_puts) == 1
        updated_vocab = json.loads(vocab_puts[0]["content"])
        assert "meeting" in updated_vocab["work"]
        assert "project" in updated_vocab["work"]
        # Deduplication: "project" appears only once
        assert updated_vocab["work"].count("project") == 1

    async def test_skips_vocabulary_update_when_no_keywords(self):
        """No vocabulary write when classify_text returns empty keywords."""

        async def fake_get_repo_contents(repo_info, path=""):
            return [{"name": "work", "type": "dir"}]

        async def fake_get_github_file(repo_info, path):
            if path == "vocabulary.json":
                return None
            if path.startswith("income/"):
                return ("Some content", "sha_note")
            return None

        put_paths = []

        async def fake_put(repo_info, path, content, commit_message):
            put_paths.append(path)
            return True

        with (
            patch("src.categorization.get_repo_contents", side_effect=fake_get_repo_contents),
            patch("src.categorization.get_github_file", side_effect=fake_get_github_file),
            patch("src.categorization.put_github_file", side_effect=fake_put),
            patch("src.categorization.delete_github_file", AsyncMock(return_value=True)),
            patch(
                "src.categorization.classify_text",
                AsyncMock(return_value=json.dumps({"category": "work", "keywords": []})),
            ),
        ):
            result = await categorize_note(_TEST_REPO, "note.md", "Some content")

        assert result == "work"
        # Only the file move put, no vocabulary update
        assert put_paths == ["work/note.md"]

    async def test_returns_none_when_classification_fails(self):
        """Returns None when AI returns None."""

        async def fake_get_repo_contents(repo_info, path=""):
            return []

        async def fake_get_github_file(repo_info, path):
            return None

        with (
            patch("src.categorization.get_repo_contents", side_effect=fake_get_repo_contents),
            patch("src.categorization.get_github_file", side_effect=fake_get_github_file),
            patch("src.categorization.classify_text", AsyncMock(return_value=None)),
        ):
            result = await categorize_note(_TEST_REPO, "note.md", "Some content")

        assert result is None


class TestCategorizeAllIncome:
    """Trophy integration: mock at external boundary, test full pipeline."""

    async def test_processes_markdown_files(self):
        """Processes .md files and skips .gitkeep and directories."""

        async def fake_get_repo_contents(repo_info, path=""):
            if path == "":
                return [{"name": "work", "type": "dir"}]
            if path == "income":
                return [
                    {"name": "note1.md", "type": "file"},
                    {"name": "note2.md", "type": "file"},
                    {"name": ".gitkeep", "type": "file"},
                    {"name": "subfolder", "type": "dir"},
                ]
            return []

        async def fake_get_github_file(repo_info, path):
            if path == "vocabulary.json":
                return None
            if path.startswith("income/") and path.endswith(".md"):
                return ("content", "sha")
            return None

        with (
            patch("src.categorization.get_repo_contents", side_effect=fake_get_repo_contents),
            patch("src.categorization.get_github_file", side_effect=fake_get_github_file),
            patch("src.categorization.put_github_file", AsyncMock(return_value=True)),
            patch("src.categorization.delete_github_file", AsyncMock(return_value=True)),
            patch(
                "src.categorization.classify_text",
                AsyncMock(return_value=json.dumps({"category": "work", "keywords": []})),
            ),
        ):
            result = await categorize_all_income(_TEST_REPO)

        assert result == 2

    async def test_vocabulary_included_in_classification_prompt(self):
        """Vocabulary loaded once and included in every classify_text prompt."""
        vocab = {"work": ["project"]}
        captured_prompts = []

        async def fake_classify(prompt):
            captured_prompts.append(prompt)
            return json.dumps({"category": "work", "keywords": []})

        async def fake_get_repo_contents(repo_info, path=""):
            if path == "":
                return [{"name": "work", "type": "dir"}]
            if path == "income":
                return [{"name": "note1.md", "type": "file"}]
            return []

        async def fake_get_github_file(repo_info, path):
            if path == "vocabulary.json":
                return (json.dumps(vocab), "sha")
            if path.startswith("income/"):
                return ("content", "sha")
            return None

        with (
            patch("src.categorization.get_repo_contents", side_effect=fake_get_repo_contents),
            patch("src.categorization.get_github_file", side_effect=fake_get_github_file),
            patch("src.categorization.put_github_file", AsyncMock(return_value=True)),
            patch("src.categorization.delete_github_file", AsyncMock(return_value=True)),
            patch("src.categorization.classify_text", side_effect=fake_classify),
        ):
            await categorize_all_income(_TEST_REPO)

        assert len(captured_prompts) == 1
        assert "project" in captured_prompts[0]

    async def test_returns_zero_on_empty_folder(self):
        """Returns 0 when income folder is empty."""

        async def fake_get_repo_contents(repo_info, path=""):
            if path == "":
                return []
            if path == "income":
                return []
            return []

        async def fake_get_github_file(repo_info, path):
            return None

        with (
            patch("src.categorization.get_repo_contents", side_effect=fake_get_repo_contents),
            patch("src.categorization.get_github_file", side_effect=fake_get_github_file),
        ):
            result = await categorize_all_income(_TEST_REPO)

        assert result == 0

    async def test_counts_only_successful_categorizations(self):
        """Only counts files where classification succeeded."""
        call_count = 0

        async def fake_classify(prompt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return json.dumps({"category": "work", "keywords": []})
            return None

        async def fake_get_repo_contents(repo_info, path=""):
            if path == "":
                return [{"name": "work", "type": "dir"}]
            if path == "income":
                return [
                    {"name": "note1.md", "type": "file"},
                    {"name": "note2.md", "type": "file"},
                ]
            return []

        async def fake_get_github_file(repo_info, path):
            if path == "vocabulary.json":
                return None
            if path.startswith("income/"):
                return ("content", "sha")
            return None

        with (
            patch("src.categorization.get_repo_contents", side_effect=fake_get_repo_contents),
            patch("src.categorization.get_github_file", side_effect=fake_get_github_file),
            patch("src.categorization.put_github_file", AsyncMock(return_value=True)),
            patch("src.categorization.delete_github_file", AsyncMock(return_value=True)),
            patch("src.categorization.classify_text", side_effect=fake_classify),
        ):
            result = await categorize_all_income(_TEST_REPO)

        assert result == 1
