ENV_BIN = ./env/bin

.PHONY: clean test make_env

clean:
	rm -rf dist build src/goattp.egg-info __pycache__
	find src -name "*.pyc" -delete
	find tests -name "*.pyc" -delete

test: env
	$(ENV_BIN)/pytest tests

make_env: env

env: environment.yml
	conda env create --force --prefix=env

