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

.PHONY: build-image
build-image:
	docker build -t backup_script:local .

.PHONY: build-image-full
build-image-full:
	# Build full image including optional heavy tools (Mongo/SQLServer). This increases image size.
	docker build \
		--build-arg INSTALL_MONGO=true \
		--build-arg INSTALL_MSSQL=false \
		-t backup_script:full .

.PHONY: push-image
push-image:
	# Tag and push to Docker Hub (set DOCKERHUB_REPO env var e.g. youruser/backup_script)
	@if [ -z "$(DOCKERHUB_REPO)" ]; then echo "Set DOCKERHUB_REPO=youruser/backup_script"; exit 1; fi
	docker tag backup_script:local $(DOCKERHUB_REPO):latest
	docker push $(DOCKERHUB_REPO):latest

.PHONY: docker-help
docker-help:
	@echo "=== Docker Targets ==="
	@echo "make build-image         - Build Docker image with common DB clients"
	@echo "make build-image-full    - Build image with MongoDB and optional SQL Server tools"
	@echo "make push-image          - Push image to Docker Hub (set DOCKERHUB_REPO)"
	@echo ""
	@echo "=== PowerShell Script (Windows) ==="
	@echo ".\\scripts\\run_backup_docker.ps1 -DbType postgres -Database mydb -User postgres"
	@echo ".\\scripts\\run_backup_docker.ps1 -DbType mysql -Database mydb -User root -Compress zip"
	@echo ""
	@echo "See DOCKER.md for detailed Docker documentation."

.PHONY: clean-docker
clean-docker:
	# Remove all backup_script images and containers
	docker ps -a -f status=exited -q | xargs -r docker rm
	docker images | grep backup_script | awk '{print $$3}' | xargs -r docker rmi

.PHONY: docker-shell
docker-shell:
	# Open interactive shell inside Docker container (for debugging)
	docker run --rm -it backup_script:local bash

