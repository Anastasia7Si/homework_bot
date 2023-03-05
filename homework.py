import logging
import os
import time
from http import HTTPStatus
import requests

import telegram

from dotenv import load_dotenv


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
    except telegram.error.TelegramError as sending_error:
        logger.error(f'Отправка сообщения невозможна: {sending_error}')
    else:
        logger.debug(f'Сообщение успешно отправлено'
                     f'на CHAT_ID: {TELEGRAM_CHAT_ID}!')


def get_api_answer(current_timestamp) -> dict:
    """Запрос к API и проверка статусов работ."""
    timestamp = current_timestamp
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            raise Exception(
                f'Некорректный статус код: {response.status_code}'
            )
        return response.json()
    except Exception as e:
        raise (f'Возникла ошибка: {e}')


def check_response(response) -> list:
    """Проверка корректности ответа API."""
    if not isinstance(response, dict):
        raise TypeError('Некорректный ответ от API!')
    homework = response.get('homeworks')
    if not isinstance(homework, list):
        raise TypeError('Домашние задания пришли не ввиде списка!')
    return homework


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
        logger.debug('Нет изменений в статусе домашних работ.')
    if homework_status in HOMEWORK_VERDICTS:
        verdict = HOMEWORK_VERDICTS[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    raise KeyError(
        f'Домашняя работа имеет неизвестный статус: {homework_status}.')


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = 0
    check_result = check_tokens()
    if check_result is False:
        logger.critical('Проблемы с переменными окружения')
        raise SystemExit('Проблемы с переменными окружения')

    while True:
        try:
            response = get_api_answer(current_timestamp)
            if 'current_date' in response:
                current_timestamp = response['current_date']
            homework = check_response(response)
            if homework is not None:
                message = parse_status(homework)
                if message is not None:
                    send_message(bot, message)
            time.sleep(RETRY_PERIOD)
        except Exception as error:
            return f'Сбой в работе программы: {error}'
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
