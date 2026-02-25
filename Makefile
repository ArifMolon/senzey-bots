.PHONY: lint type test dev install clean

lint:
	ruff check .

type:
	mypy src/

test:
	pytest tests/

dev:
	streamlit run src/senzey_bots/ui/main.py

install:
	uv sync

clean:
	rm -rf .ruff_cache .mypy_cache .pytest_cache
