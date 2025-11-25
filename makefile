run-db:
	docker-compose up -d

stop-db:
	docker-compose down

reset-db:
	docker-compose down -v
	docker-compose up -d

install:
	pip install -r requirements.txt

shell:
	# Linux / macOS
	source venv/bin/activate
	# Windows
	# venv\Scripts\activate

test:
	pytest -vv --maxfail=1

lint:
	flake8 src/

freeze:
	pip freeze > requirements.txt
