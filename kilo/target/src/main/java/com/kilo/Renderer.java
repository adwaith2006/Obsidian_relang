package com.kilo;

public class Renderer {

    public void refreshScreen(Editor editor) {
        StringBuilder abuf = new StringBuilder();

        int screenrows = editor.getScreenrows();
        int screencols = editor.getScreencols();
        int numrows = editor.getNumrows();

        abuf.append("\u001b[?25l"); /* Hide cursor */
        abuf.append("\u001b[H");    /* Go home */

        for (int y = 0; y < screenrows; y++) {
            int filerow = editor.getRowoff() + y;

            if (filerow >= numrows) {
                if (numrows == 0 && y == screenrows / 3) {
                    String welcome = String.format("Kilo editor -- version %s", Editor.KILO_VERSION);
                    int welcomelen = welcome.length();
                    if (welcomelen > screencols) {
                        welcomelen = screencols;
                    }
                    int padding = (screencols - welcomelen) / 2;
                    if (padding > 0) {
                        abuf.append("~");
                        padding--;
                    }
                    while (padding-- > 0) {
                        abuf.append(" ");
                    }
                    abuf.append(welcome.substring(0, welcomelen));
                } else {
                    abuf.append("~");
                }
                abuf.append("\u001b[0K\r\n");
                continue;
            }

            EditorRow r = editor.getRows().get(filerow);
            int len = r.getRsize() - editor.getColoff();
            int currentColor = -1;

            if (len > 0) {
                if (len > screencols) {
                    len = screencols;
                }
                String renderStr = r.getRender();
                int[] hl = r.getHl();
                int coloff = editor.getColoff();

                for (int j = 0; j < len; j++) {
                    char c = (coloff + j < renderStr.length()) ? renderStr.charAt(coloff + j) : ' ';
                    int hlType = (hl != null && coloff + j < hl.length) ? hl[coloff + j] : SyntaxHighlightDB.HL_NORMAL;

                    if (hlType == SyntaxHighlightDB.HL_NONPRINT) {
                        abuf.append("\u001b[7m");
                        char sym = (c <= 26) ? (char) ('@' + c) : '?';
                        abuf.append(sym);
                        abuf.append("\u001b[0m");
                    } else if (hlType == SyntaxHighlightDB.HL_NORMAL) {
                        if (currentColor != -1) {
                            abuf.append("\u001b[39m");
                            currentColor = -1;
                        }
                        abuf.append(c);
                    } else {
                        int color = SyntaxHighlightDB.syntaxToColor(hlType);
                        if (color != currentColor) {
                            abuf.append(String.format("\u001b[%dm", color));
                            currentColor = color;
                        }
                        abuf.append(c);
                    }
                }
            }
            abuf.append("\u001b[39m");
            abuf.append("\u001b[0K");
            abuf.append("\r\n");
        }

        /* Status bar row 1 */
        abuf.append("\u001b[0K");
        abuf.append("\u001b[7m");

        String fname = (editor.getFilename() != null) ? editor.getFilename() : "[No Name]";
        if (fname.length() > 20) {
            fname = fname.substring(0, 20);
        }
        String status = String.format("%s - %d lines %s", fname, numrows, (editor.getDirty() > 0) ? "(modified)" : "");
        String rstatus = String.format("%d/%d", editor.getRowoff() + editor.getCy() + 1, numrows);

        int slen = status.length();
        if (slen > screencols) {
            slen = screencols;
            status = status.substring(0, slen);
        }
        abuf.append(status);

        int rlen = rstatus.length();
        while (slen < screencols) {
            if (screencols - slen == rlen) {
                abuf.append(rstatus);
                break;
            } else {
                abuf.append(" ");
                slen++;
            }
        }
        abuf.append("\u001b[0m\r\n");

        /* Status bar row 2 */
        abuf.append("\u001b[0K");
        String msg = editor.getStatusmsg();
        long now = System.currentTimeMillis() / 1000L;
        if (msg != null && !msg.isEmpty() && (now - editor.getStatusmsgTime() < 5)) {
            int msglen = Math.min(msg.length(), screencols);
            abuf.append(msg.substring(0, msglen));
        }

        /* Cursor positioning */
        int cx = 1;
        int filerow = editor.getRowoff() + editor.getCy();
        if (filerow < numrows) {
            EditorRow row = editor.getRows().get(filerow);
            int coloff = editor.getColoff();
            int limit = editor.getCx() + coloff;
            for (int j = coloff; j < limit; j++) {
                if (j < row.size() && row.getChars().charAt(j) == KeyAction.TAB) {
                    cx += 7 - (cx % 8);
                }
                cx++;
            }
        }

        abuf.append(String.format("\u001b[%d;%dH", editor.getCy() + 1, cx));
        abuf.append("\u001b[?25h"); /* Show cursor */

        System.out.print(abuf);
        System.out.flush();
    }
}
