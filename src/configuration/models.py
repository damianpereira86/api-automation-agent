from enum import Enum


class Model(Enum):
    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"
    O1_PREVIEW = "o1-preview"
    O1_MINI = "o1-mini"
    O3_MINI = "o3-mini"
    GPT_4_TURBO = "gpt-4-turbo"
    CLAUDE_SONNET_3_5 = "claude-3-5-sonnet-latest"
    CLAUDE_SONNET_3_7 = "claude-3-7-sonnet-latest"
    CLAUDE_HAIKU_3_5 = "claude-3-5-haiku-latest"

    def is_anthropic(self):
        return self in [
            Model.CLAUDE_HAIKU_3_5,
            Model.CLAUDE_SONNET_3_5,
            Model.CLAUDE_SONNET_3_7,
        ]
