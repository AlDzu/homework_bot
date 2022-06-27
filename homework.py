import logging
import os
import time
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG,
    filename='main.log',
    filemode='w'
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
logger.addHandler(handler)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Oтправляет сообщение в Telegram чат."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
        )
    except Exception as error:
        logging.error(f'Ошибка при отправке: {error}')


def get_api_answer(current_timestamp):
    """Делает запрос к эндпоинту API-сервиса"""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    homework_statuses = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if homework_statuses.status_code != 200:
        message = f'Сбой в работе программы: {homework_statuses.status_code}'
        logging.error(message)
        raise requests.ConnectionError(message)
    return homework_statuses.json()


def check_response(response):
    """Проверяет ответ API на корректность"""
    if not type(response['homeworks']) is dict \
            and response['current_date'] is not None:
        return response['homeworks']
    else:
        logging.error(f'Неожиданный ответ API: {response}')


def parse_status(homework):
    """Извлекает из информации статус работы"""
    homework_name = homework['homework_name']
    homework_status = homework['status']

    try:
        verdict = HOMEWORK_STATUSES[homework_status]
    except Exception as error:
        logging.error(f'Неизвестный сатус работы: {error} {homework_status}')
        raise error

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения"""
    if PRACTICUM_TOKEN is not None \
            and TELEGRAM_TOKEN is not None \
            and TELEGRAM_CHAT_ID is not None:
        return True
    else:
        return False


def main():
    """Основная логика работы бота."""
    bot = Bot(token=TELEGRAM_TOKEN)

    status_last_hw_1 = 'reviewing'
    # При первом запуске считаем что работа проверяется

    while True:
        try:
            current_timestamp = int(
                (datetime.today() - timedelta(days=30)).timestamp()
            )
            response = get_api_answer(current_timestamp)
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            logging.error(message)
            time.sleep(RETRY_TIME)
        else:
            if check_tokens():
                homework = check_response(response)
                status_last_hw = homework[0]['status']  # Текущий статус работы
                message = parse_status(homework[0])
            else:
                message = 'Недостоверные значения исходных перменных!'
                send_message(bot, message)
                logging.critical(message)

            if status_last_hw != status_last_hw_1:
                logging.info(f'Сообщение "{message}" успешно отправлено!')
                status_last_hw_1 = status_last_hw
            else:
                message = 'Статус работы не изменился'
                logging.debug(message)


if __name__ == '__main__':
    main()
