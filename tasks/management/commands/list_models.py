# from django.core.management.base import BaseCommand
# from django.apps import apps

# class Command(BaseCommand):
#     help = "List all models, their corresponding apps, and the fields of each model"

#     def handle(self, *args, **kwargs):
#         self.stdout.write("Listing all apps, their models, and the fields:\n")
#         for app_config in apps.get_app_configs():
#             self.stdout.write(f"\nApp: {app_config.name}")
#             for model in app_config.get_models():
#                 fields = model._meta.get_fields()  # Get all fields of the model
#                 field_names = [field.name for field in fields]
#                 field_count = len(fields)
#                 self.stdout.write(f"    Model: {model.__name__} ({field_count} fields)")
#                 self.stdout.write("        Fields:")
#                 for field_name in field_names:
#                     self.stdout.write(f"            - {field_name}")
