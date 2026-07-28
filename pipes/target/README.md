# pipes (Rust)

Animated Unicode box-drawing pipes terminal screensaver — faithful Rust port of the Python reference implementation.

## Build (Linux / WSL)

```bash
# Install Rust if not present
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env

# Build release binary inside target/
cd pipes/target
cargo build --release

# Binary is at:
./target/release/pipes
```

## Run

```bash
# Default — 1 pipe, heavy box-drawing style, 75 fps
./target/release/pipes

# Multiple pipes, random start, curved style
./target/release/pipes -p 5 -R -P 1

# All options
./target/release/pipes --help
```

## CLI Options

| Flag | Long | Default | Description |
|------|------|---------|-------------|
| `-p` | `--pipes` | 1 | Number of pipes |
| `-f` | `--fps` | 75 | Frames per second (20-100) |
| `-s` | `--steady` | 13 | Steadiness / turn probability (3-15) |
| `-r` | `--limit` | 2000 | Characters drawn before screen reset |
| `-R` | `--random` | off | Random start positions & directions |
| `-B` | `--no-bold` | off | Disable bold text |
| `-C` | `--no-color` | off | Disable ANSI colors |
| `-K` | `--keep-style` | off | Keep pipe style on wrap |
| `-P` | `--pipe-style` | 0 | Pipe character set (0-9) |

## Pipe Styles

| # | Name | Characters |
|---|------|-----------|
| 0 | Heavy | `┃ ━ ┏ ┓ ┗ ┛` |
| 1 | Curved | `│ ─ ╭ ╮ ╯ ╰` |
| 2 | Light | `│ ─ ┌ ┐ ┘ └` |
| 3 | Double | `║ ═ ╔ ╗ ╝ ╚` |
| 4 | Knobby | `\| - + ` |
| 5 | Angles | `\| / \\` |
| 6 | Dots | `. o` |
| 7 | Dots_O | `. o` |
| 8 | Slashes | `- \\ /` |
| 9 | Mixed | `╿ ╼ ┍ ┑ ┚ ┕` |

## Submit (reLang)

```bash
source ../setup.sh
relang "./pipes/target/target/release/pipes"
```

## Keys

Press **Ctrl-C** to quit.
