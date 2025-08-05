from loguru import logger
from telegram import Telegram

if __name__ == '__main__':
    logger.info('Start notifying')

    with Telegram() as tele:
        tele.send_message('send sample message', parse_mode=None)
