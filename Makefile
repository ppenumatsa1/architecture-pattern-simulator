PYTHON ?= ./.venv/bin/python

.PHONY: up down restart lint format test

up:
	docker compose up -d --build

down:
	docker compose down

restart: down up

lint:
	$(PYTHON) -m ruff check .
	cd ui && npm run lint

format:
	$(PYTHON) -m ruff format .
	cd ui && npm run format

test:
	@$(PYTHON) -m pytest; status=$$?; if [ $$status -eq 5 ]; then echo "No Python tests collected yet."; else exit $$status; fi
	cd ui && npm run test
