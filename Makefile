.PHONY: help up down logs backend frontend worker test build lint clean seed \
        deploy-backend deploy-mobile secret

help:
	@echo "Biazmark — common commands"
	@echo "  make up              Start full stack (docker compose)"
	@echo "  make down            Stop stack"
	@echo "  make logs            Tail logs"
	@echo "  make backend         Run backend only (local, no docker)"
	@echo "  make frontend        Run frontend only (local)"
	@echo "  make worker          Run worker only (local)"
	@echo "  make seed            Seed demo business + kick off pipeline"
	@echo "  make test            Run backend tests"
	@echo "  make lint            Ruff + TS check"
	@echo "  make build           Build backend image + frontend bundle"
	@echo "  make secret          Generate a strong SECRET_KEY"
	@echo "  make deploy-backend  Deploy backend to Fly.io (see DEPLOY.md)"
	@echo "  make deploy-mobile   Build signed Android APK"
	@echo "  make clean           Remove volumes & build artefacts"

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f --tail=100

backend:
	cd backend && uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

worker:
	cd backend && arq app.worker.WorkerSettings

seed:
	python scripts/seed_demo.py

test:
	cd backend && pytest -q

lint:
	cd backend && ruff check app tests
	cd frontend && npm run lint || true

build:
	docker build -t biazmark-backend:latest backend
	cd frontend && npm ci && npm run build

secret:
	@./scripts/generate-secret.sh

deploy-backend:
	./scripts/deploy-backend-fly.sh

deploy-mobile:
	./scripts/build-mobile-apk.sh

clean:
	docker compose down -v
	rm -rf backend/.pytest_cache backend/__pycache__ frontend/.next frontend/node_modules
