all: dist
.PHONY: dist
dist: venv/manifest.txt
	./venv/bin/poetry build

.PHONY: mount
mount:
	@echo "make mount is not needed in LibreLane 2+. You may simply call 'librelane --dockerized'."

.PHONY: pdk pull-librelane
pdk pull-librelane:
	@echo "LibreLane 2+ will automatically pull PDKs and/or Docker containers when it needs them."

.PHONY: librelane
librelane:
	@echo "make librelane is deprecated. Please use make docker-image."
	@echo "----"
	@$(MAKE) docker-image

.PHONY: docker-image
docker-image:
	cat $(shell nix build --no-link --print-out-paths .#librelane-docker -L --verbose) | docker load

.PHONY: docs
docs:
	$(MAKE) -C docs html

.PHONY: host-docs
host-docs:
	python3 -m http.server --directory ./docs/build/html
	
.PHONY: watch-docs
watch-docs:
	nodemon\
		-w .\
		-e md,py,css\
		-i "docs/build/**/*"\
		-i "docs/build/*"\
		-i "docs/source/reference/*_vars.md"\
		-i "docs/source/reference/flows.md"\
		-x "$(MAKE) docs && python3 -m http.server --directory docs/build/html"

.PHONY: lint
lint:
	black --check .
	flake8 .
	mypy --check-untyped-defs .

.PHONY: coverage-infrastructure
coverage-infrastructure:
	python3 -m pytest -n auto\
		--cov=librelane --cov-config=.coveragerc --cov-report html:htmlcov_infra --cov-report term

.PHONY: coverage-steps
coverage-steps:
	python3 -m pytest -n auto\
		--cov=librelane.steps --cov-config=.coveragerc-steps --cov-report html:htmlcov_steps --cov-report term\
		--step-rx "." -k test_all_steps

.PHONY: check-license
check-license: venv/manifest.txt
	./venv/bin/python3 -m pip freeze > ./requirements.frz.txt
	docker run -v `pwd`:/volume \
		-it --rm pilosus/pip-license-checker \
		java -jar app.jar \
		--requirements '/volume/requirements.frz.txt'

venv: venv/manifest.txt
venv/manifest.txt: ./pyproject.toml
	rm -rf venv
	python3 -m venv ./venv
	PYTHONPATH= ./venv/bin/python3 -m pip install --upgrade pip
	PYTHONPATH= ./venv/bin/python3 -m pip install --upgrade wheel poetry poetry-plugin-export
	PYTHONPATH= ./venv/bin/poetry export --with dev --without-hashes --format=requirements.txt --output=requirements_tmp.txt
	PYTHONPATH= ./venv/bin/python3 -m pip install --upgrade -r requirements_tmp.txt
	PYTHONPATH= ./venv/bin/python3 -m pip freeze > $@
	@echo ">> Venv prepared."

.PHONY: veryclean
veryclean: clean
veryclean:
	rm -rf venv/

.PHONY: clean
clean:
	rm -rf build/
	rm -rf logs/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf designs/*/runs
	rm -rf test_data/designs/*/runs
	rm -rf test/designs/*/runs
