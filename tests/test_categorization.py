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
            result = await get_existing_categories("token", "owner", "repo")

        assert "income" not in result
        assert "trash" not in result
        assert "work" in result
        assert "personal" in result
        assert len(result) == 2

    async def test_returns_empty_list_on_empty_repo(self):
        """Returns empty list when no categories exist."""
        with patch("src.categorization.get_repo_contents", AsyncMock(return_value=[])):
            result = await get_existing_categories("token", "owner", "repo")

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
            result = await get_vocabulary_from_repo("token", "owner", "repo")
        assert result == vocab

    async def test_returns_empty_dict_when_file_missing(self):
        """Returns {} when vocabulary.json does not exist."""
        with patch("src.categorization.get_github_file", AsyncMock(return_value=None)):
            result = await get_vocabulary_from_repo("token", "owner", "repo")
        assert result == {}

    async def test_returns_empty_dict_on_invalid_json(self):
        """Returns {} when vocabulary.json is not valid JSON."""
        with patch(
            "src.categorization.get_github_file",
            AsyncMock(return_value=("not valid json {{{", "sha123")),
        ):
            result = await get_vocabulary_from_repo("token", "owner", "repo")
        assert result == {}


class TestUpdateVocabularyInRepo:
    """Test vocabulary.json update in GitHub repo."""

    async def test_merges_new_keywords(self):
        """New keywords are merged with existing ones."""
        existing = {"work": ["project"]}
        put_calls = []

        async def fake_put(token, owner, repo, path, content, commit_message):
            put_calls.append(json.loads(content))
            return True

        with (
            patch(
                "src.categorization.get_github_file",
                AsyncMock(return_value=(json.dumps(existing), "sha")),
            ),
            patch("src.categorization.put_github_file", side_effect=fake_put),
        ):
            await update_vocabulary_in_repo("token", "owner", "repo", "work", ["deadline"])

        assert len(put_calls) == 1
        assert "project" in put_calls[0]["work"]
        assert "deadline" in put_calls[0]["work"]

    async def test_deduplicates_keywords(self):
        """Duplicate keywords are removed."""
        existing = {"work": ["project", "deadline"]}
        put_calls = []

        async def fake_put(token, owner, repo, path, content, commit_message):
            put_calls.append(json.loads(content))
            return True

        with (
            patch(
                "src.categorization.get_github_file",
                AsyncMock(return_value=(json.dumps(existing), "sha")),
            ),
            patch("src.categorization.put_github_file", side_effect=fake_put),
        ):
            await update_vocabulary_in_repo("token", "owner", "repo", "work", ["project", "sprint"])

        assert put_calls[0]["work"].count("project") == 1
        assert "sprint" in put_calls[0]["work"]

    async def test_caps_at_50_keywords(self):
        """Keywords are capped at 50 per category."""
        existing_keywords = [f"word{i}" for i in range(48)]
        existing = {"work": existing_keywords}
        put_calls = []

        async def fake_put(token, owner, repo, path, content, commit_message):
            put_calls.append(json.loads(content))
            return True

        with (
            patch(
                "src.categorization.get_github_file",
                AsyncMock(return_value=(json.dumps(existing), "sha")),
            ),
            patch("src.categorization.put_github_file", side_effect=fake_put),
        ):
            await update_vocabulary_in_repo(
                "token", "owner", "repo", "work", ["new1", "new2", "new3", "new4"]
            )

        assert len(put_calls[0]["work"]) == 50

    async def test_creates_new_category_entry(self):
        """Creates new vocabulary entry when category doesn't exist yet."""
        put_calls = []

        async def fake_put(token, owner, repo, path, content, commit_message):
            put_calls.append(json.loads(content))
            return True

        with (
            patch("src.categorization.get_github_file", AsyncMock(return_value=None)),
            patch("src.categorization.put_github_file", side_effect=fake_put),
        ):
            await update_vocabulary_in_repo(
                "token", "owner", "repo", "new_category", ["word1", "word2"]
            )

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
            result = await move_github_file(
                "token", "owner", "repo", "income/note.md", "work/note.md"
            )

        assert result is True

    async def test_returns_false_when_file_not_found(self):
        """Returns False when source file doesn't exist."""
        with patch("src.categorization.get_github_file", AsyncMock(return_value=None)):
            result = await move_github_file(
                "token", "owner", "repo", "income/note.md", "work/note.md"
            )

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
            result = await move_github_file(
                "token", "owner", "repo", "income/note.md", "work/note.md"
            )

        assert result is False


class TestCategorizeNote:
    """Test single note categorization."""

    async def test_categorizes_and_moves_note(self):
        """Note is classified and moved to category folder."""
        with (
            patch(
                "src.categorization.get_existing_categories",
                AsyncMock(return_value=["work", "personal"]),
            ),
            patch(
                "src.categorization.get_vocabulary_from_repo",
                AsyncMock(return_value={}),
            ),
            patch(
                "src.categorization.classify_note",
                AsyncMock(return_value=("work", ["meeting", "project"])),
            ),
            patch("src.categorization.move_github_file", AsyncMock(return_value=True)),
            patch("src.categorization.update_vocabulary_in_repo", AsyncMock()) as mock_update,
        ):
            result = await categorize_note("token", "owner", "repo", "note.md", "Meeting notes")

        assert result == "work"
        mock_update.assert_called_once()

    async def test_skips_vocabulary_update_when_no_keywords(self):
        """update_vocabulary_in_repo is not called when classify_note returns no keywords."""
        with (
            patch("src.categorization.get_existing_categories", AsyncMock(return_value=[])),
            patch("src.categorization.get_vocabulary_from_repo", AsyncMock(return_value={})),
            patch(
                "src.categorization.classify_note",
                AsyncMock(return_value=("work", [])),
            ),
            patch("src.categorization.move_github_file", AsyncMock(return_value=True)),
            patch("src.categorization.update_vocabulary_in_repo", AsyncMock()) as mock_update,
        ):
            result = await categorize_note("token", "owner", "repo", "note.md", "Some content")

        assert result == "work"
        mock_update.assert_not_called()

    async def test_returns_none_when_classification_fails(self):
        """Returns None when classification fails."""
        with (
            patch("src.categorization.get_existing_categories", AsyncMock(return_value=[])),
            patch("src.categorization.get_vocabulary_from_repo", AsyncMock(return_value={})),
            patch(
                "src.categorization.classify_note",
                AsyncMock(return_value=(None, [])),
            ),
        ):
            result = await categorize_note("token", "owner", "repo", "note.md", "Some content")

        assert result is None


class TestCategorizeAllIncome:
    """Test batch categorization of income folder."""

    async def test_processes_markdown_files(self):
        """Processes .md files and skips others."""
        mock_contents = [
            {"name": "note1.md", "type": "file"},
            {"name": "note2.md", "type": "file"},
            {"name": ".gitkeep", "type": "file"},
            {"name": "subfolder", "type": "dir"},
        ]

        with (
            patch("src.categorization.get_repo_contents", AsyncMock(return_value=mock_contents)),
            patch(
                "src.categorization.get_github_file",
                AsyncMock(return_value=("content", "sha")),
            ),
            patch(
                "src.categorization.get_vocabulary_from_repo",
                AsyncMock(return_value={}),
            ),
            patch("src.categorization.categorize_note", AsyncMock(return_value="work")),
        ):
            result = await categorize_all_income("token", "owner", "repo")

        assert result == 2

    async def test_passes_vocabulary_to_categorize_note(self):
        """Loads vocabulary once and passes it to each categorize_note call."""
        mock_contents = [
            {"name": "note1.md", "type": "file"},
        ]
        vocab = {"work": ["project"]}
        captured_calls = []

        async def fake_categorize(
            token, owner, repo, name, content, existing_categories, vocabulary
        ):
            captured_calls.append(vocabulary)
            return "work"

        with (
            patch("src.categorization.get_repo_contents", AsyncMock(return_value=mock_contents)),
            patch(
                "src.categorization.get_github_file",
                AsyncMock(return_value=("content", "sha")),
            ),
            patch(
                "src.categorization.get_vocabulary_from_repo",
                AsyncMock(return_value=vocab),
            ),
            patch("src.categorization.categorize_note", side_effect=fake_categorize),
        ):
            await categorize_all_income("token", "owner", "repo")

        assert len(captured_calls) == 1
        assert captured_calls[0] == vocab

    async def test_returns_zero_on_empty_folder(self):
        """Returns 0 when income folder is empty."""
        with (
            patch("src.categorization.get_repo_contents", AsyncMock(return_value=[])),
            patch("src.categorization.get_vocabulary_from_repo", AsyncMock(return_value={})),
        ):
            result = await categorize_all_income("token", "owner", "repo")

        assert result == 0

    async def test_counts_only_successful_categorizations(self):
        """Only counts successfully categorized files."""
        mock_contents = [
            {"name": "note1.md", "type": "file"},
            {"name": "note2.md", "type": "file"},
        ]

        with (
            patch("src.categorization.get_repo_contents", AsyncMock(return_value=mock_contents)),
            patch(
                "src.categorization.get_github_file",
                AsyncMock(return_value=("content", "sha")),
            ),
            patch(
                "src.categorization.get_vocabulary_from_repo",
                AsyncMock(return_value={}),
            ),
            patch(
                "src.categorization.categorize_note",
                AsyncMock(side_effect=["work", None]),
            ),
        ):
            result = await categorize_all_income("token", "owner", "repo")

        assert result == 1
