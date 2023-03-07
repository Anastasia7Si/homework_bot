class TheAnswerIsNot200Error(Exception):
    """Ответ сервера не равен 200."""


class RequestExceptionError(Exception):
    """Ошибка запроса."""


class UnchangedStatusError(Exception):
    """Нет изменений статуса."""
