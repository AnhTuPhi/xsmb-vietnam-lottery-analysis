from loguru import logger
from telegram import Telegram
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

if __name__ == '__main__':
    logger.info('Start notifying')

    with Telegram() as tele:

        captions = [
            "Amount of day from last appearing \nSố ngày từ lần xuất hiện cuối cùng giải ĐẶC BIỆT",
            "Top 10 amount of day from last appearing \nTop 10 số lâu chưa xuất hiện giải ĐẶC BIỆT",
            "Phân tích chi tiêt ma trận heatmap",
            "Phân tích top 10 bộ số hay xuất hiện trong vòng 1 năm",
            "Phân tích phân bổ trong vòng 1 năm",
            "Amount of day from last appearing \nSố ngày từ lần xuất hiện cuối cùng",
            "Top 10 amount of day from last appearing \nTop 10 số lâu chưa xuất hiện",
        ]
        photos = [
            open('images/special_delta.jpg', 'rb').read(),
            open('images/special_delta_top_10.jpg', 'rb').read(),
            open('images/heatmap.jpg', 'rb').read(),
            open('images/top-10.jpg', 'rb').read(),
            open('images/distribution.jpg', 'rb').read(),
            open('images/delta.jpg', 'rb').read(),
            open('images/delta_top_10.jpg', 'rb').read(),
        ]
        tele.send_group_media(photos, captions, parse_mode="HTML")

        with open('SPECIAL_PRIZE_NOTI.md', 'r', encoding='utf-8') as f:
            text = f.read()
        tele.send_message(text, parse_mode=None)
