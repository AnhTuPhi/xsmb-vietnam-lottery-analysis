
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
from loguru import logger
from lottery import Lottery

if __name__ == '__main__':
    lottery = Lottery()
    lottery.load()

    # Fetch latest data
    begin_date = lottery.get_last_date()
    tz = ZoneInfo('Asia/Ho_Chi_Minh')
    now = datetime.now(tz)
    last_date = now.date()

    if now.time() < time(18, 35):
        last_date -= timedelta(days=1)

    delta = (last_date - begin_date).days + 1
    for i in range(1, delta):
        selected_date = begin_date + timedelta(days=i)
        logger.info("Fetching: {}", selected_date)
        lottery.fetch(selected_date)

    lottery.generate_dataframes()
    lottery.dump()
