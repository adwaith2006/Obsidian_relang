# sl (Go port)

Steam locomotive running across your terminal — faithful Go port of the original C/Python sl.

## Build (Linux / WSL)

```bash
# Install Go if not present
sudo apt install -y golang-go

# Build from target/ directory
cd sl/target
go build -o sl sl.go

# Run
./sl
```

## Run Options

```bash
./sl           # Default D51 locomotive
./sl -c        # C51 locomotive
./sl -l        # Small "logo" SL locomotive
./sl -a        # Accident mode (people on tracks)
./sl -F        # Fly mode (locomotive lifts off)
./sl -d        # Dance mode
./sl -lll      # Logo SL with 3 extra cars
```

## No-build run (Go source directly)

```bash
cd sl/target
go run sl.go
```

## Submit (reLang)

```bash
cd /path/to/Obsidian_relang
source setup.sh
relang "sl/target/sl"
```
