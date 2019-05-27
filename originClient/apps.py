from django.apps import AppConfig


class TestdeleteConfig(AppConfig):
    name = 'originClient'
    def ready(self):
        from originClient import updater
        updater.start()