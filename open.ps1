python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m flask --app local_app db upgrade
.venv\Scripts\python -m flask --app local_app seed-samples
.venv\Scripts\python -m flask --app local_app run --port 5001