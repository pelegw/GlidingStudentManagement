# training_records/apps.py
from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.dispatch import receiver

class TrainingRecordsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'training_records'

    def ready(self):
        # Import and setup signals
        import training_records.middleware
        training_records.middleware.setup_audit_signals()
        # Run data import after migration
        post_migrate.connect(self._post_migrate_callback, sender=self)
    def _post_migrate_callback(self, sender, **kwargs):
        from django.core.management import call_command
        call_command('import_initial_data')