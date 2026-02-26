.PHONY: all exam solution clean

PROJECT_ROOT := ../..
TEXSMITH := uv --project $(PROJECT_ROOT) run texsmith
BUILD_DIR := build
SOURCES := $(wildcard *.md)
TEMPLATE := $(PROJECT_ROOT)/src/texsmith_template_exam/exam
MAIN := $(basename $(firstword $(SOURCES)))

all: exam solution

exam:
	$(TEXSMITH) -o$(BUILD_DIR)/exam -t$(TEMPLATE) config.yml $(SOURCES) --build
	mv $(BUILD_DIR)/exam/$(MAIN).pdf $(BUILD_DIR)/exam/exam.pdf

solution:
	$(TEXSMITH) -o$(BUILD_DIR)/solution -t$(TEMPLATE) config.yml $(SOURCES) --build -a solution=true
	mv $(BUILD_DIR)/solution/$(MAIN).pdf $(BUILD_DIR)/solution/solution.pdf

clean:
	rm -rf $(BUILD_DIR)
