.DEFAULT_GOAL := help

help:        ## list targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "} {printf "  %-12s %s\n", $$1, $$2}'

test:        ## run host pytest suite
	.venv/bin/pytest -q

lint:        ## ruff lint
	.venv/bin/ruff check src/ tests/

fix:         ## ruff auto-fix
	.venv/bin/ruff check --fix src/ tests/

sim:         ## launch host simulator
	.venv/bin/python tools/sim.py

upload:      ## push src/ to a connected device via mpremote (see /firmware)
	./tools/upload.sh

flash:       ## flash MicroPython firmware (see /firmware)
	./tools/flash.sh

repl:        ## open mpremote REPL
	./tools/repl.sh

logs:        ## tail /firmware serial-capture logs
	@mkdir -p logs && tail -F logs/*.log 2>/dev/null || echo "no logs yet -- start a firmware session"

clean:       ## remove cache dirs
	rm -rf __pycache__ src/**/__pycache__ tests/__pycache__ .pytest_cache .ruff_cache

.PHONY: help test lint fix sim upload flash repl logs clean
