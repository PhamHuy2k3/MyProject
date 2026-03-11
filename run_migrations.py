import os
import django
from django.core.management import call_command
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MyProject.settings')
django.setup()

try:
    with open('migration_output.txt', 'w', encoding='utf-8') as f:
        print("Running makemigrations MyApp...", file=f)
        call_command('makemigrations', 'MyApp', stdout=f, stderr=f)
        print("Running migrate...", file=f)
        call_command('migrate', stdout=f, stderr=f)
    print("Migration script completed successfully.")
except Exception as e:
    with open('migration_error.txt', 'w', encoding='utf-8') as f:
        f.write(str(e))
    print(f"Error running migrations: {e}")
