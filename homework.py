import logging
import os
import time

import json
import requests
import telegram

from dotenv import load_dotenv
from http import HTTPStatus


load_dotenv()


PRACTICUM_TOKEN = os.getenv('TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEG_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEG_CHAT_ID')


RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logging.basicConfig(
    handlers=[logging.StreamHandler()],
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

logger = logging.getLogger(__name__)


class TheAnswerIsNot200Error(Exception):
    """Ответ сервера не равен 200."""


class RequestExceptionError(Exception):
    """Ошибка запроса."""


class UnchangedStatusError(Exception):
    """Нет изменений статуса."""


def check_tokens() -> bool:
    """Проверка доступности переменных окружения."""
    for token in (PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID):
        if token is None:
            logger.critical(
                'Отсутствует обязательная переменная окружения: '
                f'"{token}"!')
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def send_message(bot, message: str) -> None:
    """Отправка сообщений в чат Телеграмм."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(f'Сообщение успешно отправлено'
                     f'на CHAT_ID: {TELEGRAM_CHAT_ID}!')
    except telegram.error.TelegramError as sending_error:
        logger.error(f'Отправка сообщения невозможна: {sending_error}')


def get_api_answer(current_timestamp: int) -> dict:
    """Запрос к API и проверка статусов работ."""
    timestamp = current_timestamp
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            raise TheAnswerIsNot200Error(
                f'Некорректный статус код: {response.status_code}'
            )
        return response.json()
    except requests.exceptions.RequestException as request_error:
        raise RequestExceptionError(
            f'Код ответа API: {request_error}'
        )
    except json.JSONDecodeError as value_error:
        raise json.JSONDecodeError(
            f'Код ответа API: {value_error}')


def check_response(response) -> list:
    """Проверка корректности ответа API."""
    if not isinstance(response, dict):
        raise TypeError('Некорректный ответ от API!')
    homeworks = response.get('homeworks')
    if 'homeworks' not in response or 'current_date' not in response:
        raise KeyError('Отсутствует ключ')
    if not isinstance(homeworks, list):
        raise TypeError('Домашние задания пришли не ввиде списка!')
    return homeworks


def parse_status(homework):
    """Извлечение из информации о конкретной домашней."""
    """работе её статуса работы."""
    if not isinstance(homework, dict):
        raise TypeError('Переменная "homework" не является словарём!')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_name is None:
        raise KeyError('Отсутствует ключ "homework_name"!')
    if homework_status is None:
        raise UnchangedStatusError('Нет изменений в статусе домашних работ.')
    if homework_status in HOMEWORK_VERDICTS:
        verdict = HOMEWORK_VERDICTS[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    raise KeyError(
        f'Домашняя работа имеет неизвестный статус: {homework_status}.')


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    old_homework_status = ''
    if not check_tokens():
        exit('Отсутсвуют переменные окружения')

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if homework != old_homework_status:
                send_message(bot, parse_status(homework))
            time.sleep(RETRY_PERIOD)
        except Exception as error:
            return f'Сбой в работе программы: {error}'
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
