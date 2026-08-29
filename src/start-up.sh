#!/usr/bin/env bash
# Steps before starting development on a pulled branch
# Create the virtualenv
python3 -m venv env
# Activate the virtual env and install requirements
source env/bin/activate && pip install -r requirements.txt
# Remove the entire db and migrations since sometimes you have local migrations that can mess with things pulled from master.
sudo rm db.sqlite3
sudo rm -rf core/migrations
# migrations and static files
python manage.py makemigrations core
python manage.py migrate
python manage.py collectstatic --noinput
# give apache required permissions
sudo chgrp www-data .
sudo chmod 777 ./db.sqlite3
# Load fixtures. questions.json has the questions, and db.json has everything else.
python manage.py loaddata db.json
python manage.py loaddata questions.json
