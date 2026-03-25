#!/usr/bin/env bash
# exit on error
set -o errexit

echo "Installing requirements..."
pip install -r requirements.txt

echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "Running migrations..."
python manage.py migrate

echo "Checking for database dump..."
if [ -f datadump.json ]; then
    echo "Loading data from datadump.json..."
    python manage.py loaddata datadump.json
    
    echo "Data loaded successfully. Renaming file to prevent reloading on next deploy..."
    mv datadump.json datadump_loaded.json.bak
fi

echo "Build process completed!"
