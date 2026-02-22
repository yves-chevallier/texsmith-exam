.PHONY: all exam solution clean

PROJECT_ROOT := ../..
TEXSMITH := uv --project $(PROJECT_ROOT) run texsmith
BUILD_DIR := build
CONFIG := config.yml
SOURCES := $(wildcard *.md)
TEMPLATE := $(PROJECT_ROOT)/src/texsmith_template_exam/exam

all: exam solution

exam:
	$(TEXSMITH) -o$(BUILD_DIR)/exam -t$(TEMPLATE) $(CONFIG) $(SOURCES) --build
	mv $(BUILD_DIR)/exam/main.pdf $(BUILD_DIR)/exam/exam.pdf

solution:
	$(TEXSMITH) -o$(BUILD_DIR)/solution -t$(TEMPLATE) $(CONFIG) $(SOURCES) --build -a solution=true
	mv $(BUILD_DIR)/solution/main.pdf $(BUILD_DIR)/solution/solution.pdf

clean:
	rm -rf $(BUILD_DIR)
