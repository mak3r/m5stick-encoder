.DEFAULT_GOAL := help

help:        ## list targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "} {printf "  %-12s %s\n", $$1, $$2}'

bootstrap:   ## create .venv using python3.13 or python3.11 (errors if neither found)
	@PYTHON=$$(command -v python3.13 || command -v python3.11 || true); \
	if [ -z "$$PYTHON" ]; then \
		echo "Error: python3.13 or python3.11 required (pyproject.toml: requires-python = \">=3.11\")"; \
		echo "Install via: brew install python@3.13"; \
		exit 1; \
	fi; \
	echo "Using $$PYTHON"; \
	$$PYTHON -m venv .venv; \
	.venv/bin/pip install --quiet --upgrade pip ruff pytest; \
	echo "venv ready. Run: source .venv/bin/activate  (or use .venv/bin/ prefix)"

test:        ## run host pytest suite
	.venv/bin/pytest -q

lint:        ## ruff lint
	.venv/bin/ruff check src/ tests/

fix:         ## ruff auto-fix
	.venv/bin/ruff check --fix src/ tests/

mpy-check:   ## verify src/ imports cleanly under MicroPython unix port
	MICROPYPATH="$(PWD)/src:$(PWD)/vendor" micropython tools/mpy_import_check.py

sim:         ## launch host simulator
	.venv/bin/python tools/sim.py

prep:        ## remove UIFlow 2 bloat and assert free space (run once on fresh device)
	./tools/device_prep.sh

upload:      ## push src/ to a connected device via mpremote (run `make prep` first on fresh device)
	./tools/upload.sh

flash:       ## flash MicroPython firmware (see /firmware)
	./tools/flash.sh

repl:        ## open mpremote REPL
	./tools/repl.sh

logs:        ## tail /firmware serial-capture logs
	@mkdir -p logs && tail -F logs/*.log 2>/dev/null || echo "no logs yet -- start a firmware session"

clean:       ## remove cache dirs
	rm -rf __pycache__ src/**/__pycache__ tests/__pycache__ .pytest_cache .ruff_cache

.PHONY: help bootstrap test lint fix mpy-check sim prep upload flash repl logs clean
