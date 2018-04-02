import logging
import threading
import time

from django.utils.timezone import now

from boocoin.mining import mine_block
from boocoin.models import Block

logger = logging.getLogger(__name__)


def start_waiting_for_blocks():
    t = threading.Thread(target=wait_for_blocks)
    t.setDaemon(True)
    t.start()


def wait_for_blocks():
    while True:
        check_for_block()
        time.sleep(30)


def check_for_block():
    # Get the active block
    active_block = Block.get_active_block()

    # Calculate how many minutes it has been since that block
    minutes_passed = (now() - active_block.time).total_seconds() / 60

    # Mine a new block if it has been 10 minutes
    if minutes_passed >= 10:
        logger.info('10 minutes passed, mining new block...')
        mine_block()
