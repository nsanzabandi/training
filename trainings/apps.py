from django.apps import AppConfig

class TrainingsConfig(AppConfig):
    name = 'trainings'

    def ready(self):
        import trainings.signals
