"""
Agent custom exceptions
"""


class AgentException(Exception):
    """Agent base exception"""
    pass


class IntentAnalysisException(AgentException):
    """Intent analysis exception"""
    pass


class QueryBuildException(AgentException):
    """Query build exception"""
    pass


class DataProcessingException(AgentException):
    """Data processing exception"""
    pass


class LLMException(AgentException):
    """LLM call exception"""
    pass


class ReportGenerationException(AgentException):
    """Report generation exception"""
    pass


class AgentHistoryException(AgentException):
    """Agent history save/load exception"""
    pass
