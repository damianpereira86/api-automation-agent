from enum import Enum


class Model(Enum):
    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"
    O1_PREVIEW = "o1-preview"
    O1_MINI = "o1-mini"
    GPT_4_TURBO = "gpt-4-turbo"
    GPT_3_5_TURBO = "gpt-3.5-turbo"
    CLAUDE_SONNET = "claude-3-5-sonnet-20241022"

    def is_anthropic(self):
        return self.value in [Model.CLAUDE_SONNET]


class DataSource(Enum):
    SWAGGER = "swagger"
    POSTMAN = "postman"
