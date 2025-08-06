from pathlib import Path

from loguru import logger
from telegram import Telegram


def send_all_images_as_album_with_caption(bot, folder_path="images", text=""):
    folder = Path(folder_path)
    valid_exts = {".jpg", ".jpeg", ".png"}
    image_paths = sorted([p for p in folder.iterdir() if p.suffix.lower() in valid_exts])

    photos = []
    captions = []

    for idx, p in enumerate(image_paths):
        with open(p, "rb") as f:
            photos.append(f.read())
        if idx == 0:
            captions.append(text)  # group caption
        else:
            captions.append(None)  # hide caption for other items

    return bot.send_group_media(photos, captions=captions, parse_mode="HTML")

if __name__ == '__main__':
    logger.info('Start notifying')

    with Telegram() as tele:

        # captions = ["Test notification analysis", None, None]
        # photos = [open('images/delta.jpg', 'rb').read(), open('images/distribution.jpg', 'rb').read(), open('images/heatmap.jpg', 'rb').read(),]
        # tele.send_message('Báo cáo tổng hợp', parse_mode=None)
        # tele.send_group_media(photos, captions, parse_mode="HTML")
        send_all_images_as_album_with_caption(tele, "images", "Nhẹ mà\nGồng tiếp chờ điểm DCA nếu bay tiếp\nCòn k thì gồng lãi")
