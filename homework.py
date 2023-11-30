import logging
import os
import sys
import time
import telegram

import requests

from http import HTTPStatus

from dotenv import load_dotenv

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяем доступность переменных окружения."""
    return (
        PRACTICUM_TOKEN is not None
        and TELEGRAM_TOKEN is not None
        and TELEGRAM_CHAT_ID is not None
    )


def send_message(bot, message):
    """Отправляет сообщение в телеграм."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug('Сообщение отправлено')
    except Exception:
        logging.error('Сообщение не отправлено')


def get_api_answer(timestamp):
    """Проверяем API на доступность."""
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp})
        response.raise_for_status()
    except requests.RequestException:
        raise ConnectionError()

    if response.status_code == HTTPStatus.OK:
        return response.json()
    raise ConnectionError()


def check_response(response: dict):
    """Проверяем запрос полученный от API."""
    if not isinstance(response, dict):
        raise TypeError("Ответ не является словарем")

    homeworks = response.get('homeworks')

    if not isinstance(homeworks, list):
        raise TypeError("Данные под ключом 'homeworks' не являются списком")
    return homeworks


def parse_status(homework):
    """Парсим API и получаем данные о статусе домашки."""
    status = homework.get('status')
    homework_name = homework.get('homework_name')

    if status is None or homework_name is None:
        raise ValueError('Отсутствует ключ "status" или "homework_name"')

    if status not in HOMEWORK_VERDICTS:
        raise ValueError('Недокументированный статус')

    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    if not check_tokens():
        logging.critical('Отсутствует необходимая переменная')
        sys.exit(1)

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if not homeworks:
                continue
            message = parse_status(homeworks[0])
            if message != '':
                send_message(bot, message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            response = 'Ошибка при запросе к основному API'
            logging.error(response)
            logging.error(message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
