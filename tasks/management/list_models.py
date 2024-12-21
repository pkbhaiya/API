from django.core.management.base import BaseCommand
from django.apps import apps

class Command(BaseCommand):
    help = "List all models and their corresponding apps"

    def handle(self, *args, **kwargs):
        self.stdout.write("Listing all apps and their models:\n")
        for app_config in apps.get_app_configs():
            self.stdout.write(f"App: {app_config.name}")
            for model in app_config.get_models():
                self.stdout.write(f"    Model: {model.__name__}")
