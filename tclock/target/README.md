# tclock (Rust Migration)

A complete, high-performance Rust port of the `tclock` terminal clock application.

## Subsystems & Architecture

| Component | Go Reference Implementation | Rust Implementation |
|---|---|---|
| **Terminal I/O & Raw Mode** | `fortio.org/terminal` | `crossterm 0.28` |
| **CLI Argument Parsing** | `flag` package | `clap 4.5` (derive interface) |
| **Date & Time** | `time` / `fortio.org/duration` | `chrono 0.4` |
| **7-Segment Digits** | `bignum` package | `src/bignum.rs` |
| **Vector Analog Clock** | `analog.go` (Bresenham + half blocks) | `src/analog.rs` |
| **Anti-Aliased Analog Clock**| `image.go` (Xiaolin Wu line AA) | `src/image_clock.rs` |
| **Tailing Mode** | `stdin.go` (TimeoutReader) | `src/tail.rs` |

## Build Instructions (Linux / WSL)

```bash
# 1. Ensure Rust toolchain is installed
source ~/.cargo/env

# 2. Build release binary
cd tclock/target
cargo build --release

# Binary is at:
./target/release/tclock
```

## Supported Modes & Flags

```bash
./target/release/tclock                      # Default 12-hour digital clock
./target/release/tclock --24                  # 24-hour time format
./target/release/tclock --analog              # Vector analog clock
./target/release/tclock --aa                  # Smooth anti-aliased analog clock
./target/release/tclock --box                 # Outline rounded box around clock
./target/release/tclock --color yellow        # Change clock color
./target/release/tclock --countdown 5m       # 5-minute countdown timer
./target/release/tclock --until "2026-12-31 23:59:59" # Countdown until date
./target/release/tclock --tail logfile.txt    # Tail log file with clock anchored top-right
tail -f logfile.txt | ./target/release/tclock --tail - # Tail stdin with clock top-right
./target/release/tclock "12:34:56"            # Print 7-segment representation and exit
```

## Keyboard Controls

- **`q`** or **`Ctrl+C`**: Graceful exit & terminal restoration
- **`a`**: Toggle anti-aliased (AA) analog clock mode
- **`c`**: Toggle continuous sub-second rendering
- **Mouse Left Click**: Toggle mouse tracking / position drag
