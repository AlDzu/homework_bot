import logging
import os
import time
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

log_folder_name = f'log-{datetime.today()}'
os.mkdir(log_folder_name)
log_trek = __file__
log_trek = '/'.join(log_trek.split('/')[:-1])
log_trek = f'{log_trek}/{log_folder_name}'

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG,
    filename=f'{log_trek}/main.log',
    filemode='w'
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
logger.addHandler(handler)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 6
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
    """Делает запрос к эндпоинту API-сервиса."""
    # Если значение в промежутке от начала проекта до текущей даты,
    # то похоже на правду

    if (current_timestamp < 1549962000
            or current_timestamp > time.time()):
        message = f'Проверить дату/время {current_timestamp}'
        logging.error(message)
        raise ValueError(message)

    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}

    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != 200:
            message = f'Неожиданный статус API {response.status_code}'
            logging.error(message)
            raise ConnectionError(message)
    except Exception as error:
        message = f'Сбой при запросе API: {error}, {response}'
        logging.error(message)
        raise error(message)

    response = response.json()

    if 'error' in response or 'code' in response:
        message = f'Неожиданный ответ API {response}'
        logging.error(message)
        raise RuntimeError(message)

    return response


def check_response(response):
    """Проверяет ответ API на корректность."""
    if (not type(response['homeworks']) is dict
            and response['current_date'] is not None):
        return response['homeworks']
    else:
        logging.error(f'Неожиданный ответ API: {response}')


def parse_status(homework):
    """Извлекает из информации статус работы."""
    if 'status' not in homework.keys():
        message = 'Неизвестный ключ вместо status'
        logger.error(message)
        raise KeyError(message)
    homework_name = homework['homework_name']
    homework_status = homework['status']

    try:
        verdict = HOMEWORK_STATUSES[homework_status]
    except Exception as error:
        logging.error(f'Неизвестный сатус работы: {error} {homework_status}')
        raise error

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    result = all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])
    return result


def main():
    """Основная логика работы бота."""
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
    except Exception as error:
        message = f'Что-то не так с ботом: {error}'
        send_message(bot, message)
        logging.error(message)
        raise ValueError(message)

    bot_init = bot.get_me()

    if (bot_init['id'] != ':'.join(TELEGRAM_TOKEN.split(':')[:-1])
       and bot_init['is_bot'] is not True):
        message = f'Что-то не так с ботом: {bot_init}'
        send_message(bot, message)
        logging.error(message)
        raise ValueError(message)

    status_last_hw_1 = 'reviewing'
    # При первом запуске считаем что работа проверяется
    if check_tokens():
        while True:
            try:
                current_timestamp = datetime.today() - timedelta(days=30)
                current_timestamp = int(current_timestamp.timestamp())
                response = get_api_answer(current_timestamp)
            except Exception as error:
                message = f'Сбой в работе программы: {error}'
                send_message(bot, message)
                logging.error(message)
            finally:
                time.sleep(RETRY_TIME)

            homework = check_response(response)
            status_last_hw = homework[0]['status']  # Текущий статус работы
            message = parse_status(homework[0])
            if status_last_hw != status_last_hw_1:
                send_message(bot, message)
                logging.info(f'Сообщение "{message}" успешно отправлено!')
                status_last_hw_1 = status_last_hw
            else:
                message = 'Статус работы не изменился'
                logging.debug(message)
    else:
        message = 'Недостоверные значения исходных перменных!'
        send_message(bot, message)
        logging.critical(message)


if __name__ == '__main__':
    main()
