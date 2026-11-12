PYTHON ?= python3

all: dist
.PHONY: dist
dist: venv/manifest.txt
	./venv/bin/poetry build

.PHONY: mount
mount:
	@echo "make mount is not needed in LibreLane. You may simply call 'librelane --dockerized'."

.PHONY: pdk pull-openlane pull-librelane
pdk pull-openlane pull-librelane:
	@echo "LibreLane will automatically pull PDKs and/or Docker containers when it needs them."

.PHONY: openlane librelane
librelane openlane:
	@echo "make librelane is deprecated. Please use make docker-image."
	@echo "----"
	@$(MAKE) docker-image

.PHONY: docker-image
docker-image:
	cat $(shell nix build --no-link --print-out-paths .#librelane-docker -L --verbose) | docker load

# double-installing is still fast
.PHONY: docs
docs:
	@if [[ -n "$(VIRTUAL_ENV)" ]]; then PYTHONPATH= $(PYTHON) -m pip install -r ./docs/requirements.txt; fi
	$(MAKE) -C docs html

.PHONY: host-docs
host-docs:
	$(PYTHON) -m http.server --directory ./docs/build/html
	
.PHONY: watch-docs
watch-docs:
	watchexec \
		-r \
		-e md,css,py \
		--ignore "*docs/build/*" \
		--ignore "*docs/source/reference/*_vars.md" \
		--ignore "*docs/source/reference/flows.md" \
		-- $(MAKE) docs '&&' $(PYTHON) -m http.server --directory docs/build/html

.PHONY: lint
lint:
	black --check .
	flake8 .
	mypy --check-untyped-defs .

.PHONY: coverage-infrastructure
coverage-infrastructure:
	$(PYTHON) -m pytest -n auto\
		--cov=librelane --cov-config=.coveragerc --cov-report html:htmlcov_infra --cov-report term

.PHONY: coverage-steps
coverage-steps:
	$(PYTHON) -m pytest -n auto\
		--cov=librelane.steps --cov-config=.coveragerc-steps --cov-report html:htmlcov_steps --cov-report term\
		-k test_all_steps

venv: venv/manifest.txt
venv/manifest.txt: ./pyproject.toml
	rm -rf venv
	$(PYTHON) -m venv ./venv
	PYTHONPATH= ./venv/bin/python3 -m pip install --upgrade pip
	PYTHONPATH= ./venv/bin/python3 -m pip install --upgrade wheel poetry
	PYTHONPATH= ./venv/bin/python3 -m pip install --upgrade --group lint --group test -e .
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
