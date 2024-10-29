@echo off
color a
cd checkin-app
call venv\Scripts\activate
pip install --upgrade -r requirements.txt
pip freeze > requirements.txt
flask run
