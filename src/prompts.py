"""LLM prompt strings."""

CLEANUP_PROMPT_BASE = (
    "Clean up this voice transcription. Your primary goal is to capture the speaker's "
    "intent — NOT to rephrase or rewrite their words.\n\n"
    "Rules:\n"
    "1. Remove filler words and false starts (ну, то есть, аа, эм, like, you know, etc.).\n"  # noqa: RUF001
    "2. Fix obvious transcription errors (misheard words, garbled phrases). "
    "If unsure what a garbled word means, leave it as-is.\n"
    "3. Do NOT rephrase, restructure, or add information.\n"
    "4. Preserve the original language. Fix punctuation minimally.\n"
    "5. If two fragments were concatenated without a break, split into sentences.\n"
    "Return only the cleaned text, nothing else.\n"
)

# Template variables: {categories_list}, {vocab_hint}, {text}
# vocab_hint should include a leading newline when non-empty, or be an empty string.
CATEGORIZE_PROMPT_TEMPLATE = (
    "Analyze this note and return JSON only:\n"
    '{{"category": "<name>", "keywords": ["word1", "word2"]}}\n\n'
    "Keywords: domain-specific words/phrases from this note that characterize the category "
    "(up to 5). These help recognize similar notes and fix transcription errors.\n\n"
    "Rules for category:\n"
    "1. If the note fits an existing category, return that category name exactly.\n"
    "2. If no existing category fits, suggest a new short name "
    "(1-2 words, lowercase, no spaces, use underscores).\n\n"
    "Existing categories: {categories_list}"
    "{vocab_hint}\n\n"
    "Note:\n{text}"
)
