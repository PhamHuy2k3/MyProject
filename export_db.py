import os
import sys
import django
from django.core.management import call_command

sys.path.append(r'c:\ITC_Subjects_HKV\Django\FinalProject\MyProject')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MyProject.settings')
django.setup()

output_file = r'c:\ITC_Subjects_HKV\Django\FinalProject\MyProject\datadump.json'

with open(output_file, 'w', encoding='utf-8') as f:
    try:
        call_command(
            'dumpdata',
            natural_foreign=True,
            natural_primary=True,
            indent=2,
            exclude=['contenttypes', 'auth.permission', 'admin.logentry', 'sessions.session'],
            stdout=f
        )
        print("Export successful.")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Export failed: {e}")
