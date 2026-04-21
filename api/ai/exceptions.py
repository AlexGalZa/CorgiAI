class AIServiceError(Exception):
    pass


class AIRateLimitError(AIServiceError):
    pass


class AIResponseError(AIServiceError):
    pass
