from loguru import logger
from telegram import Telegram
import time

def send_noti_base_analyze() -> None:
    with Telegram() as telegram:
        message = "Phân tích XSMB"
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
            open('data/base_analyze/images/special_delta.jpg', 'rb').read(),
            open('data/base_analyze/images/special_delta_top_10.jpg', 'rb').read(),
            open('data/base_analyze/images/heatmap.jpg', 'rb').read(),
            open('data/base_analyze/images/top-10.jpg', 'rb').read(),
            open('data/base_analyze/images/distribution.jpg', 'rb').read(),
            open('data/base_analyze/images/delta.jpg', 'rb').read(),
            open('data/base_analyze/images/delta_top_10.jpg', 'rb').read(),
        ]
        telegram.send_group_media(photos, captions, parse_mode="HTML")
        telegram.send_message(message, parse_mode=None)


def send_noti_gap_hard_analyze() -> None:
    message = "Phân tích dự đoán KQXS theo kỹ thuật phân tích Gap Hazard"
    captions = [
        "Gap Hazard Function Comparison"
    ]
    photos = [
        open('data/gap_hazard_analyze/images/hazard_compare.png', 'rb').read(),
    ]

    with Telegram() as telegram:
        telegram.send_group_media(photos, captions, parse_mode="HTML")
        telegram.send_message(message, parse_mode=None)

if __name__ == '__main__':
    logger.info('Executing analyzing notification')

    send_noti_base_analyze()
    logger.info('--> 1. Already sent base analyze')
    time.sleep(60)

    send_noti_gap_hard_analyze()
    logger.info('--> 2. Already sent gap hazard analyze')



