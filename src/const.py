"""Shared constants."""

PROVIDER_GROQ = "groq"
PROVIDER_WIT = "wit"
PROVIDER_GEMINI = "gemini"
PROVIDER_ANTHROPIC = "anthropic"
PROVIDER_OPENAI = "openai"
PROVIDER_OPENROUTER = "openrouter"
PROVIDER_QWEN = "qwen"
PROVIDER_DEEPSEEK = "deepseek"

TELEGRAM_STARS_CURRENCY = "XTR"
STAR_TO_DOLLAR = 0.014

SOURCE_TELEGRAM = "telegram"
SOURCE_WHATSAPP = "whatsapp"

GEMINI_API_BASE = "https://generativelanguage.googleapis.com"
ANTHROPIC_API_BASE = "https://api.anthropic.com"
OPENAI_API_BASE = "https://api.openai.com"
GROQ_API_BASE = "https://api.groq.com"
OPENROUTER_API_BASE = "https://openrouter.ai"
QWEN_API_BASE = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
DEEPSEEK_API_BASE = "https://api.deepseek.com/v1"
GITHUB_API_BASE = "https://api.github.com"
EXCLUDED_CATEGORIES = ("income", "trash")

# AI generation parameters
CLASSIFY_MAX_TOKENS = 50
GPT_CHAT_MAX_TOKENS = 2048
GPT_CHAT_TEMPERATURE = 0.7

ROLE_VIP = "vip"
ROLE_TESTER = "tester"
ROLE_BLOCKED = "blocked"

SECONDS_PER_TOKEN = 20

PRIVATE_CHAT_TYPE = "private"
CHAT_PREFIX_USER = "u_"
CHAT_PREFIX_GROUP = "g_"
