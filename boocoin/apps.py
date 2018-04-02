from django.apps import AppConfig



class BoocoinConfig(AppConfig):
    name = 'boocoin'

    def ready(self):
        from boocoin.timer import start_waiting_for_blocks
        start_waiting_for_blocks()
