#! /bin/bash
# Call this before pushing branch
source env/bin/activate
# Steps before pushing
# 1. Saving requirements
sudo pip freeze > requirements.txt
# 2. If something needs to be saved to fixtures do so. Example for questions.json
# sudo python manage.py dumpdata --indent 4 core.question > fixtures/questions.json
