.PHONY: demo demo-exam demo-pset demo-quiz demo-clean

DEMO_DIR := demo

# Build all demo outputs (exam + solution) for each demo

demo:
	$(MAKE) -C $(DEMO_DIR)/exam all
	$(MAKE) -C $(DEMO_DIR)/pset all
	$(MAKE) -C $(DEMO_DIR)/quiz all

# Build individual demos

demo-exam:
	$(MAKE) -C $(DEMO_DIR)/exam all

demo-pset:
	$(MAKE) -C $(DEMO_DIR)/pset all

demo-quiz:
	$(MAKE) -C $(DEMO_DIR)/quiz all

# Clean demo build artifacts

demo-clean:
	$(MAKE) -C $(DEMO_DIR)/exam clean
	$(MAKE) -C $(DEMO_DIR)/pset clean
	$(MAKE) -C $(DEMO_DIR)/quiz clean
