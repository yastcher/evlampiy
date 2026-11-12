"""LLM prompt strings."""

GPT_SYSTEM_PROMPT = (
    "You are a helpful assistant integrated into a voice-notes Telegram bot. "
    "You have access to tools that let you look up the user's recent transcriptions, "
    "settings, and note categories. Use them when the user's question requires "
    "information about their data.\n\n"
    "Guidelines:\n"
    "- Answer concisely and helpfully.\n"
    "- Use the same language the user writes in.\n"
    "- When you use a tool, incorporate its result naturally into your answer.\n"
    "- If a tool returns an error or empty data, tell the user honestly.\n"
    "- Do not fabricate information that was not returned by a tool.\n"
)

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
    "1. Strongly prefer an existing category: if the note reasonably fits one, return that "
    "name EXACTLY. Reuse beats precision — do not split hairs.\n"
    "2. Invent a new short name (1-2 words, lowercase, no spaces, use underscores) ONLY when "
    "no existing category reasonably fits.\n"
    "3. If the note is empty, meaningless, or obvious garbage (a test, an accidental "
    'recording, gibberish), return "trash".\n\n'
    "Existing categories: {categories_list}"
    "{vocab_hint}\n\n"
    "Note:\n{text}"
)
