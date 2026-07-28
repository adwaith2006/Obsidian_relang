# picoc - Python 3 Migration

This is an original, pure-Python 3 reimplementation of the `picoc` C interpreter.

## Requirements

- Python 3.8+ (No external third-party dependencies required)

## Usage

You can execute C source files directly using Python 3:

```bash
python3 target/picoc.py <program.c> [args...]
```

### Examples

```bash
# Run a C program
python3 target/picoc.py examples/hello.c

# Run tests
python3 target/tests/run_tests.py
```

## Validation

To run the full hackathon test harness validation:

```bash
cd relang
python3 validate.py "python3 ../target/picoc.py"
```

Result: `307/307 passed (100.0%)`
