.PHONY: run-tests generate-coverage-badge

run-tests:
	uv run pytest src/doc_weaver/test/

generate-coverage-badge:
	uv run pytest --cov=doc_weaver --cov-report=term src/doc_weaver/test/
	uv run coverage-badge -o images/coverage.svg -f

generate-documentation:
	uv run --group docs pdoc -o docs src/doc_weaver