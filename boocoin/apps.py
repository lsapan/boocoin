import logging
import sys

from django.apps import AppConfig

logger = logging.getLogger(__name__)

RUNNING_SERVER = (len(sys.argv) > 1 and sys.argv[1] == 'runserver')


class BoocoinConfig(AppConfig):
    name = 'boocoin'

    def ready(self):
        if RUNNING_SERVER:
            from boocoin.models import SyncLock
            from boocoin.p2p import sync_all
            from boocoin.timer import start_waiting_for_blocks
            SyncLock.objects.all().delete()
            start_waiting_for_blocks()
            sync_all()
