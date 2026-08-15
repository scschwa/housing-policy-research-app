.PHONY: install test lint typecheck demo eval-offline eval-live graph

install:
	python -m pip install -e ".[dev]"

test:
	pytest -q

lint:
	ruff check .

typecheck:
	mypy src tests evals

demo:
	python -m housing_policy_agents.cli demo --offline --format both

eval-offline:
	npm run eval:offline

eval-live:
	npm run eval:live

graph:
	python -m housing_policy_agents.cli graph --format mermaid

