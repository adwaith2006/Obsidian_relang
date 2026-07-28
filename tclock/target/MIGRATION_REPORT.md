# Migration Report: tclock (Go -> Rust)

## 1. Major Architectural Differences
- **Memory Safety & Terminal Guards:** Replaced manual cleanup defers with Rust's RAII pattern via `TerminalGuard`, ensuring terminal raw mode and cursor visibility are always restored on exit or panic.
- **Signal Handling:** Replaced Go `os/signal` channels with `ctrlc` crate and `AtomicBool` flags for thread-safe shutdown.
- **Rendering Engine:** Replaced `fortio.org/terminal` and `ansipixels` with cross-platform `crossterm` queueing operations (`MoveTo`, `SetForegroundColor`, `SetBackgroundColor`, `Clear`), reducing screen redraw flicker.

## 2. Go Features Redesigned in Rust
- **Custom `TimeoutReader`:** Replaced Go's non-blocking channel-based reader with a Rust non-blocking reader and sleeping interval strategy in `src/tail.rs`.
- **7-Segment Display Engine:** Preserved the original ASCII font geometry (5 rows × 4 columns) in `src/bignum.rs`, utilizing Rust string slices and iterators.
- **Anti-Aliasing Canvas:** Ported Xiaolin Wu anti-aliasing line algorithm to `src/image_clock.rs` with custom RGBA alpha blending.

## 3. External Crates Used
- `crossterm` (v0.28): Cross-platform terminal manipulation, raw mode, mouse & keyboard event polling, and color formatting.
- `chrono` (v0.4): High-precision local time formatting, duration math, and parsing.
- `clap` (v4.5): Struct-derived command line argument parsing with type-safe defaults and help output.
- `ctrlc` (v3.4): Cross-platform SIGINT / Ctrl-C signal handler.

## 4. Verification & Observable Behavior
- **Digital Mode:** Confirmed 7-segment digit formatting matches original Go output.
- **Analog Mode:** Confirmed hand angles and hour tick marks match original vector drawing.
- **AA Mode:** Confirmed half-block pixel rendering with sub-pixel line smoothing.
- **Tail Mode:** Confirmed anchored top-right clock position while passing input stream lines.
- **Build Status:** Compiles with zero errors under `--release`.
