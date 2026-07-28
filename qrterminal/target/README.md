# QRTerminal (Python 3 Migration)

A Python 3 port of `qrterminal`, a terminal QR code generator library supporting full-block ANSI rendering, unicode half-block rendering, configurable quiet zones, custom block characters, error-correction levels, and Sixel output.

## Prerequisites

- Python 3.8+ (uses Python standard library without external dependencies)
- Go 1.20+ (only required to run/verify the original Go reference demo)

## Installation & Setup

No third-party packages or compilation steps are required for the Python target library.

```bash
cd target
```

## Running Demonstrations

### 1. Source Go Demo

Compile and run the Go reference implementation:

```bash
cd qrterminal/source
go run ./demo/main.go
```

Or build the CLI binary:

```bash
cd qrterminal/source
go build -o /tmp/qrterminal ./cmd/qrterminal
/tmp/qrterminal -s "https://example.com"
```

### 2. Target Python Demo

Run the migrated Python demonstration script:

```bash
python3 qrterminal/target/demo.py
```

### 3. CLI Demonstration Options

You can also import `qrterminal` in Python scripts or interactive sessions:

```python
import sys
import qrterminal

# Full-block ANSI QR code
qrterminal.generate("https://example.com", qrterminal.L, sys.stdout)

# Half-block Unicode QR code
qrterminal.generate_half_block("https://example.com", qrterminal.L, sys.stdout)
```

## Running Unit Tests

Run the complete test suite:

```bash
python3 qrterminal/target/test_qrterminal.py
```

All 8 tests cover:
- Empty and short text inputs
- Normal text encoding
- URL string encoding
- Correction levels (`L`, `M`, `Q`, `H`)
- Full-block ANSI mode
- Half-block Unicode mode
- Quiet-zone border configurations (1, 2, 4, 6)
- Sixel sequence generation
