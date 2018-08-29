ENV = env
ENV_DIR = ./$(ENV)
ENV_BIN = $(ENV_DIR)/bin

.PHONY: clean test

clean:
	rm -rf dist build src/goattp.egg-info __pycache__
	find src -name "*.pyc" -delete
	find tests -name "*.pyc" -delete

test: env
	$(ENV_BIN)/pytest tests

env: environment.yml setup.py
	conda env create --force --prefix=$(ENV_DIR)
