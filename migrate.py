import subprocess
import os

with open('migrate_output.txt', 'w', encoding='utf-8') as f:
    f.write(f"Working Directory: {os.getcwd()}\n")
    try:
        python_exe = r'C:\Users\QUOC HUY\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\python.exe'
        result = subprocess.run([python_exe, 'manage.py', 'makemigrations', '--noinput'], 
                             stdout=subprocess.PIPE, 
                             stderr=subprocess.PIPE, 
                             text=True, 
                             encoding='utf-8')
        f.write("STDOUT:\n")
        f.write(result.stdout)
        f.write("\nSTDERR:\n")
        f.write(result.stderr)
        f.write(f"\nExit Code: {result.returncode}\n")
    except Exception as e:
        f.write(f"Exception: {str(e)}\n")
