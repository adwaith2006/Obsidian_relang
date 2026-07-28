# Asciiquarium (Python 3 Port)

A Python 3 port of the ASCII aquarium / sea animation in your terminal using the standard library `curses` module.

## Prerequisites

- Python 3.6+ (uses standard library `curses`, `random`, `time`, `sys`, `argparse`, `signal`)
- A POSIX/ANSI terminal supporting curses (e.g. Linux/Ubuntu 24.04, macOS)

No third-party packages or Perl dependencies are required.

## Setup

Make the script executable:

```bash
chmod +x asciiquarium/target/asciiquarium.py
```

## Run Commands

Run the program directly using Python 3:

```bash
python3 asciiquarium/target/asciiquarium.py
```

Or execute directly if permissions are set:

```bash
./asciiquarium/target/asciiquarium.py
```

### Command Line Options

- `-c` or `--classic`: Run in classic mode (disables new fish and new monsters).

```bash
python3 asciiquarium/target/asciiquarium.py -c
```

## Interactive Controls

- `q` / `Q`: Exit the program.
- `r` / `R`: Redraw/re-initialize the aquarium scene for current window dimensions.
- `p` / `P`: Pause / unpause the animation.
- `Ctrl+C`: Exit cleanly.
