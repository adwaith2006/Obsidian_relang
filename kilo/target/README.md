# Java 21 Kilo Text Editor Migration

A complete object-oriented Java 21 port of the C Kilo text editor.

## Project Structure

- **`pom.xml`**: Maven configuration configured for Java 21 (`release 21`) with `maven-compiler-plugin`, `maven-jar-plugin`, and `exec-maven-plugin`.
- **`src/main/java/com/kilo/`**:
  - [`Main.java`](file:///c:/Users/hp/OneDrive/Documents/relang/Obsidian_relang/kilo/target/src/main/java/com/kilo/Main.java): Entry point and application setup loop.
  - [`Editor.java`](file:///c:/Users/hp/OneDrive/Documents/relang/Obsidian_relang/kilo/target/src/main/java/com/kilo/Editor.java): Core document state manager (cursor tracking, lines list, scroll offset, search state).
  - [`EditorRow.java`](file:///c:/Users/hp/OneDrive/Documents/relang/Obsidian_relang/kilo/target/src/main/java/com/kilo/EditorRow.java): Represents a document line with tab expansion, character editing, and syntax highlighting parsing.
  - [`Renderer.java`](file:///c:/Users/hp/OneDrive/Documents/relang/Obsidian_relang/kilo/target/src/main/java/com/kilo/Renderer.java): Double-buffered VT100 screen renderer using `StringBuilder` and ANSI escape sequences.
  - [`Terminal.java`](file:///c:/Users/hp/OneDrive/Documents/relang/Obsidian_relang/kilo/target/src/main/java/com/kilo/Terminal.java): Raw terminal input/output management (`stty raw -echo` / `stty sane`, window size, key code parsing).
  - [`InputHandler.java`](file:///c:/Users/hp/OneDrive/Documents/relang/Obsidian_relang/kilo/target/src/main/java/com/kilo/InputHandler.java): Keypress handler routing control actions (Save, Quit, Search, Navigation, Editing).
  - [`FileManager.java`](file:///c:/Users/hp/OneDrive/Documents/relang/Obsidian_relang/kilo/target/src/main/java/com/kilo/FileManager.java): Disk I/O operations (file reading, writing, serialization).
  - [`EditorSyntax.java`](file:///c:/Users/hp/OneDrive/Documents/relang/Obsidian_relang/kilo/target/src/main/java/com/kilo/EditorSyntax.java): Language syntax highlighting definitions (extensions, keywords, comment delimiters).
  - [`SyntaxHighlightDB.java`](file:///c:/Users/hp/OneDrive/Documents/relang/Obsidian_relang/kilo/target/src/main/java/com/kilo/SyntaxHighlightDB.java): Syntax highlighting database & ANSI color mapper.
  - [`KeyAction.java`](file:///c:/Users/hp/OneDrive/Documents/relang/Obsidian_relang/kilo/target/src/main/java/com/kilo/KeyAction.java): Key code constants for terminal control and escape sequences.

## Build

### Using Maven:
```bash
mvn clean package
```

### Using javac directly:
```bash
javac --release 21 -d classes src/main/java/com/kilo/*.java
```

## Run

### Using executable JAR:
```bash
java -jar kilo.jar <filename>
```

### Using wrapper script:
```bash
./kilo <filename>      # Linux / macOS
kilo.cmd <filename>    # Windows
```
