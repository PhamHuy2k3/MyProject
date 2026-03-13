import os
import django
from django.core.management import call_command

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MyProject.settings')
django.setup()

import sys

with open('migrate_programmatic_log.txt', 'w', encoding='utf-8') as f:
    sys.stdout = f
    sys.stderr = f
    try:
        print("Starting migrate...")
        call_command('migrate', interactive=False)
        print("Migrations completed successfully.")
    except Exception as e:
        print(f"Error: {e}")
