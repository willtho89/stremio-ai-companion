from enum import Enum


class ContentType(str, Enum):
    """Enum for content types supported by Stremio."""

    MOVIE = "movie"
    SERIES = "series"


class CatalogId(str, Enum):
    """Predefined catalog identifiers."""

    TRENDING = "trending"


class LLMProvider(str, Enum):
    OPENROUTER = "https://openrouter.ai/api/v1"
    OPENAI = "https://api.openai.com/v1"
    ANTHROPIC = "https://api.anthropic.com/v1"
    GEMINI = "https://generativelanguage.googleapis.com/v1beta/openai/"


class Languages(Enum):
    EN = ("en-US", "English")
    PT_BR = ("pt-BR", "Portuguese (Brazil)")
    PT_PT = ("pt-PT", "Portuguese (Portugal)")
    ES = ("es", "Spanish")
    FR = ("fr", "French")
    DE = ("de", "German")
    IT = ("it", "Italian")
    JA = ("ja", "Japanese")
    ZH_CN = ("zh-CN", "Chinese (Simplified)")
    ZH_TW = ("zh-TW", "Chinese (Traditional)")
    KO = ("ko", "Korean")
    RU = ("ru", "Russian")
    AR = ("ar", "Arabic")
    NL = ("nl", "Dutch")
    SV = ("sv", "Swedish")
    TR = ("tr", "Turkish")
    PL = ("pl", "Polish")
    HI = ("hi", "Hindi")

    def __init__(self, code, label):
        self.code = code
        self.label = label

    def __str__(self):
        return self.label
