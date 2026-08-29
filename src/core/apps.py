from django.apps import AppConfig
from suit.apps import DjangoSuitConfig


# better admin display for customer usability
class SuitConfig(DjangoSuitConfig):
    layout = 'horizontal'
    name = 'suit'


class CoreConfig(AppConfig):
    name = 'core'

    def ready(self):
        import core.signals
