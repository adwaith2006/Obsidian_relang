package com.kilo;

public class Main {

    public static void main(String[] args) {
        String filename = (args.length > 0) ? args[0] : null;

        Editor editor = new Editor();
        Terminal terminal = new Terminal();
        Renderer renderer = new Renderer();
        InputHandler inputHandler = new InputHandler();

        terminal.updateWindowSize(editor);
        if (filename != null) {
            FileManager.open(editor, filename);
        }
        terminal.enableRawMode();

        editor.setStatusMessage("HELP: Ctrl-S = save | Ctrl-Q = quit | Ctrl-F = find");

        while (true) {
            renderer.refreshScreen(editor);
            inputHandler.processKeypress(editor, terminal, renderer);
        }
    }
}
