# cmdb/apps.py
from django.apps import AppConfig
from neomodel import config
from django.conf import settings

class CmdbConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'cmdb'

    def ready(self):
        # This runs when the app is fully loaded
        config.DATABASE_URL = settings.NEO4J_BOLT_URL
        # Optional: you can also set other neomodel config here
        config.ENCRYPTED = False  # if needed