# Example Usage of Code Quality Tools

This document provides examples of how to use the code quality tools we've added to the project.

## Ruff

Ruff is an extremely fast Python linter and code formatter, written in Rust.

To run Ruff:

```shell
# Check all Python files
ruff check .

# Auto-fix issues where possible
ruff check --fix .

# Check a specific file
ruff check src/sub_tools/main.py
```

## Black

Black is an opinionated code formatter that ensures consistent style across your codebase.

To run Black:

```shell
# Format all Python files
black .

# Check if files are formatted correctly without modifying them
black --check .

# Format a specific file
black src/sub_tools/main.py
```

## mypy

mypy is a static type checker for Python that helps catch certain types of bugs.

To run mypy:

```shell
# Type check all Python files in src directory
mypy src

# Type check a specific file
mypy src/sub_tools/main.py

# Show more detailed errors
mypy src --show-error-codes
```

## Pre-commit

The pre-commit hooks will run automatically when committing code. You can also run them manually:

```shell
# Run on all files
pre-commit run --all-files

# Run on staged files
pre-commit run
```