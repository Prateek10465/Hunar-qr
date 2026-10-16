PY ?= python3
.PHONY: install test e2e run docker
install:
	$(PY) -m venv .venv && . .venv/bin/activate && pip install -r backend/requirements-dev.txt && cd e2e && npm install
test:
	cd backend && $(PY) -m pytest
e2e:
	cd e2e && npm test
run:
	cd backend && WEB_DIR=../web $(PY) -m uvicorn app.main:create_app --factory --reload --port 8000
docker:
	docker compose up --build
