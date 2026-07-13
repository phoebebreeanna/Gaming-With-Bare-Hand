PYTHON ?= python3

run:
	$(PYTHON) main.py

test:
	SDL_VIDEODRIVER=dummy $(PYTHON) -m unittest test_goal_detection -v

install:
	$(PYTHON) -m pip install pygame

clean:
	rm -rf __pycache__ */__pycache__

.PHONY: run test install clean
