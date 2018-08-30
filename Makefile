ENV = env
ENV_DIR = ./$(ENV)
ENV_BIN = $(ENV_DIR)/bin

.PHONY: clean test

test: env
	$(ENV_BIN)/pytest tests

clean:
	rm -rf dist build src/goattp.egg-info __pycache__
	find src -name "*.pyc" -delete
	find tests -name "*.pyc" -delete

env: environment.yml setup.py
	conda env create --force --prefix=$(ENV_DIR)
