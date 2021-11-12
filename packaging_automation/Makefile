PYTHON = python3

install:
	$(PYTHON) -m pip install -r requirements.txt

pip-compile:
	$(PYTHON) -m piptools compile --allow-unsafe

pip-sync:
	$(PYTHON) -m piptools sync

sort-requirements:
	LC_ALL=C sort -o requirements.in requirements.in

.PHONY : install pip-compile pip-sync sort-requirements
