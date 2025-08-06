from loguru import logger
from telegram import Telegram

if __name__ == '__main__':
    logger.info('Start notifying')

    with Telegram() as tele:

        captions = None
        photos = [open('images/delta.jpg', 'rb').read(), open('images/distribution.jpg', 'rb').read(), open('images/heatmap.jpg', 'rb').read(),]
        tele.send_group_media(photos, captions, parse_mode="HTML")
        tele.send_message('Báo cáo tổng hợp', parse_mode=None)
