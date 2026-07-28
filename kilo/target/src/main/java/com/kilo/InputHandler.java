package com.kilo;

public class InputHandler {

    public void processKeypress(Editor editor, Terminal terminal, Renderer renderer) {
        int c = terminal.readKey();

        switch (c) {
            case KeyAction.ENTER -> editor.insertNewline();

            case KeyAction.CTRL_C -> {
                /* Ignore Ctrl-C to prevent accidental data loss */
            }

            case KeyAction.CTRL_Q -> {
                if (editor.getDirty() > 0 && editor.getQuitTimes() > 0) {
                    editor.setStatusMessage(
                            "WARNING!!! File has unsaved changes. Press Ctrl-Q %d more times to quit.",
                            editor.getQuitTimes()
                    );
                    editor.decrementQuitTimes();
                    return;
                }
                terminal.disableRawMode();
                System.out.println("\u001b[2J\u001b[H"); /* Clear screen before exiting */
                System.exit(0);
            }

            case KeyAction.CTRL_S -> FileManager.save(editor);

            case KeyAction.CTRL_F -> editor.find(terminal, renderer);

            case KeyAction.BACKSPACE, KeyAction.CTRL_H, KeyAction.DEL_KEY -> editor.delChar();

            case KeyAction.PAGE_UP, KeyAction.PAGE_DOWN -> {
                if (c == KeyAction.PAGE_UP && editor.getCy() != 0) {
                    editor.setCy(0);
                } else if (c == KeyAction.PAGE_DOWN && editor.getCy() != editor.getScreenrows() - 1) {
                    editor.setCy(editor.getScreenrows() - 1);
                }
                int times = editor.getScreenrows();
                int dirKey = (c == KeyAction.PAGE_UP) ? KeyAction.ARROW_UP : KeyAction.ARROW_DOWN;
                while (times-- > 0) {
                    editor.moveCursor(dirKey);
                }
            }

            case KeyAction.ARROW_UP, KeyAction.ARROW_DOWN, KeyAction.ARROW_LEFT, KeyAction.ARROW_RIGHT ->
                    editor.moveCursor(c);

            case KeyAction.CTRL_L, KeyAction.ESC -> {
                /* Refresh screen / clear screen side-effect */
            }

            default -> {
                if (c >= 32 && c < 127 || c == KeyAction.TAB) {
                    editor.insertChar(c);
                }
            }
        }

        editor.resetQuitTimes();
    }
}
