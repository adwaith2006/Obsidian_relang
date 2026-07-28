package com.kilo;

import java.util.ArrayList;
import java.util.List;

public class Editor {
    public static final String KILO_VERSION = "0.0.1";
    public static final int KILO_QUIT_TIMES = 3;

    private int cx;
    private int cy;
    private int rowoff;
    private int coloff;
    private int screenrows;
    private int screencols;
    private final List<EditorRow> rows;
    private int dirty;
    private String filename;
    private String statusmsg;
    private long statusmsgTime;
    private EditorSyntax syntax;
    private int quitTimes;

    public Editor() {
        this.cx = 0;
        this.cy = 0;
        this.rowoff = 0;
        this.coloff = 0;
        this.screenrows = 24;
        this.screencols = 80;
        this.rows = new ArrayList<>();
        this.dirty = 0;
        this.filename = null;
        this.statusmsg = "";
        this.statusmsgTime = 0;
        this.syntax = null;
        this.quitTimes = KILO_QUIT_TIMES;
    }

    public int getCx() {
        return cx;
    }

    public void setCx(int cx) {
        this.cx = cx;
    }

    public int getCy() {
        return cy;
    }

    public void setCy(int cy) {
        this.cy = cy;
    }

    public int getRowoff() {
        return rowoff;
    }

    public void setRowoff(int rowoff) {
        this.rowoff = rowoff;
    }

    public int getColoff() {
        return coloff;
    }

    public void setColoff(int coloff) {
        this.coloff = coloff;
    }

    public int getScreenrows() {
        return screenrows;
    }

    public void setScreenrows(int screenrows) {
        this.screenrows = screenrows;
    }

    public int getScreencols() {
        return screencols;
    }

    public void setScreencols(int screencols) {
        this.screencols = screencols;
    }

    public List<EditorRow> getRows() {
        return rows;
    }

    public int getNumrows() {
        return rows.size();
    }

    public int getDirty() {
        return dirty;
    }

    public void setDirty(int dirty) {
        this.dirty = dirty;
    }

    public String getFilename() {
        return filename;
    }

    public void setFilename(String filename) {
        this.filename = filename;
        this.syntax = SyntaxHighlightDB.selectSyntaxHighlight(filename);
    }

    public String getStatusmsg() {
        return statusmsg;
    }

    public long getStatusmsgTime() {
        return statusmsgTime;
    }

    public EditorSyntax getSyntax() {
        return syntax;
    }

    public void setSyntax(EditorSyntax syntax) {
        this.syntax = syntax;
    }

    public int getQuitTimes() {
        return quitTimes;
    }

    public void setQuitTimes(int quitTimes) {
        this.quitTimes = quitTimes;
    }

    public void decrementQuitTimes() {
        this.quitTimes--;
    }

    public void resetQuitTimes() {
        this.quitTimes = KILO_QUIT_TIMES;
    }

    public void setStatusMessage(String fmt, Object... args) {
        try {
            this.statusmsg = String.format(fmt, args);
        } catch (Exception e) {
            this.statusmsg = fmt;
        }
        this.statusmsgTime = System.currentTimeMillis() / 1000L;
    }

    public void updateSyntaxCascade(int startRow) {
        for (int i = startRow; i < rows.size(); i++) {
            EditorRow current = rows.get(i);
            EditorRow prev = (i > 0) ? rows.get(i - 1) : null;
            boolean changed = current.updateSyntax(syntax, prev);
            if (!changed) {
                break;
            }
        }
    }

    public void insertRow(int at, String s) {
        if (at < 0 || at > rows.size()) {
            return;
        }
        EditorRow row = new EditorRow(at, s);
        rows.add(at, row);
        for (int j = at; j < rows.size(); j++) {
            rows.get(j).setIdx(j);
        }
        EditorRow prevRow = (at > 0) ? rows.get(at - 1) : null;
        row.updateRow(syntax, prevRow);
        updateSyntaxCascade(at + 1);
        dirty++;
    }

    public void delRow(int at) {
        if (at < 0 || at >= rows.size()) {
            return;
        }
        rows.remove(at);
        for (int j = at; j < rows.size(); j++) {
            rows.get(j).setIdx(j);
        }
        updateSyntaxCascade(at);
        dirty++;
    }

    public void insertChar(int c) {
        int filerow = rowoff + cy;
        int filecol = coloff + cx;

        while (rows.size() <= filerow) {
            insertRow(rows.size(), "");
        }
        EditorRow row = rows.get(filerow);
        EditorRow prevRow = (filerow > 0) ? rows.get(filerow - 1) : null;
        row.insertChar(filecol, c, syntax, prevRow);
        updateSyntaxCascade(filerow + 1);

        if (cx == screencols - 1) {
            coloff++;
        } else {
            cx++;
        }
        dirty++;
    }

    public void insertNewline() {
        int filerow = rowoff + cy;
        int filecol = coloff + cx;

        if (filerow >= rows.size()) {
            if (filerow == rows.size()) {
                insertRow(filerow, "");
            }
            fixCursorAfterNewline();
            return;
        }

        EditorRow row = rows.get(filerow);
        if (filecol >= row.size()) {
            filecol = row.size();
        }

        if (filecol == 0) {
            insertRow(filerow, "");
        } else {
            String split = row.getChars().substring(filecol);
            row.getChars().setLength(filecol);
            EditorRow prevRow = (filerow > 0) ? rows.get(filerow - 1) : null;
            row.updateRow(syntax, prevRow);
            insertRow(filerow + 1, split);
        }
        fixCursorAfterNewline();
    }

    private void fixCursorAfterNewline() {
        if (cy == screenrows - 1) {
            rowoff++;
        } else {
            cy++;
        }
        cx = 0;
        coloff = 0;
    }

    public void delChar() {
        int filerow = rowoff + cy;
        int filecol = coloff + cx;

        if (filerow >= rows.size() || (filecol == 0 && filerow == 0)) {
            return;
        }
        EditorRow row = rows.get(filerow);

        if (filecol == 0) {
            filecol = rows.get(filerow - 1).size();
            EditorRow prevRow = (filerow - 1 > 0) ? rows.get(filerow - 2) : null;
            rows.get(filerow - 1).appendString(row.getChars().toString(), syntax, prevRow);
            delRow(filerow);

            if (cy == 0) {
                if (rowoff > 0) rowoff--;
            } else {
                cy--;
            }
            cx = filecol;
            if (cx >= screencols) {
                coloff = cx - screencols + 1;
                cx = screencols - 1;
            }
        } else {
            EditorRow prevRow = (filerow > 0) ? rows.get(filerow - 1) : null;
            row.delChar(filecol - 1, syntax, prevRow);
            updateSyntaxCascade(filerow + 1);
            if (cx == 0 && coloff > 0) {
                coloff--;
            } else {
                cx--;
            }
        }
        dirty++;
    }

    public void moveCursor(int key) {
        int filerow = rowoff + cy;
        int filecol = coloff + cx;
        EditorRow row = (filerow >= rows.size()) ? null : rows.get(filerow);

        switch (key) {
            case KeyAction.ARROW_LEFT:
                if (cx == 0) {
                    if (coloff > 0) {
                        coloff--;
                    } else if (filerow > 0) {
                        cy--;
                        cx = rows.get(filerow - 1).size();
                        if (cx > screencols - 1) {
                            coloff = cx - screencols + 1;
                            cx = screencols - 1;
                        }
                    }
                } else {
                    cx--;
                }
                break;

            case KeyAction.ARROW_RIGHT:
                if (row != null && filecol < row.size()) {
                    if (cx == screencols - 1) {
                        coloff++;
                    } else {
                        cx++;
                    }
                } else if (row != null && filecol == row.size()) {
                    cx = 0;
                    coloff = 0;
                    if (cy == screenrows - 1) {
                        rowoff++;
                    } else {
                        cy++;
                    }
                }
                break;

            case KeyAction.ARROW_UP:
                if (cy == 0) {
                    if (rowoff > 0) {
                        rowoff--;
                    }
                } else {
                    cy--;
                }
                break;

            case KeyAction.ARROW_DOWN:
                if (filerow < rows.size()) {
                    if (cy == screenrows - 1) {
                        rowoff++;
                    } else {
                        cy++;
                    }
                }
                break;
        }

        /* Fix cx if current line is shorter */
        filerow = rowoff + cy;
        filecol = coloff + cx;
        row = (filerow >= rows.size()) ? null : rows.get(filerow);
        int rowlen = (row != null) ? row.size() : 0;
        if (filecol > rowlen) {
            cx -= (filecol - rowlen);
            if (cx < 0) {
                coloff += cx;
                if (coloff < 0) coloff = 0;
                cx = 0;
            }
        }
    }

    public void find(Terminal terminal, Renderer renderer) {
        StringBuilder query = new StringBuilder();
        int lastMatch = -1;
        int findNext = 0;
        int savedHlLine = -1;
        int[] savedHl = null;

        int savedCx = cx;
        int savedCy = cy;
        int savedColoff = coloff;
        int savedRowoff = rowoff;

        while (true) {
            setStatusMessage("Search: %s (Use ESC/Arrows/Enter)", query.toString());
            renderer.refreshScreen(this);

            int c = terminal.readKey();
            if (c == KeyAction.DEL_KEY || c == KeyAction.CTRL_H || c == KeyAction.BACKSPACE) {
                if (query.length() > 0) {
                    query.deleteCharAt(query.length() - 1);
                }
                lastMatch = -1;
            } else if (c == KeyAction.ESC || c == KeyAction.ENTER) {
                if (c == KeyAction.ESC) {
                    cx = savedCx;
                    cy = savedCy;
                    coloff = savedColoff;
                    rowoff = savedRowoff;
                }
                if (savedHl != null && savedHlLine >= 0 && savedHlLine < rows.size()) {
                    rows.get(savedHlLine).setHl(savedHl);
                    savedHl = null;
                }
                setStatusMessage("");
                return;
            } else if (c == KeyAction.ARROW_RIGHT || c == KeyAction.ARROW_DOWN) {
                findNext = 1;
            } else if (c == KeyAction.ARROW_LEFT || c == KeyAction.ARROW_UP) {
                findNext = -1;
            } else if (c >= 32 && c < 127) {
                query.append((char) c);
                lastMatch = -1;
            }

            if (lastMatch == -1) {
                findNext = 1;
            }

            if (findNext != 0 && query.length() > 0) {
                int matchOffset = -1;
                int current = lastMatch;
                int numrows = rows.size();

                for (int i = 0; i < numrows; i++) {
                    current += findNext;
                    if (current == -1) {
                        current = numrows - 1;
                    } else if (current == numrows) {
                        current = 0;
                    }

                    if (current >= 0 && current < numrows) {
                        String render = rows.get(current).getRender();
                        int idx = render.indexOf(query.toString());
                        if (idx != -1) {
                            matchOffset = idx;
                            break;
                        }
                    }
                }
                findNext = 0;

                /* Restore saved highlight */
                if (savedHl != null && savedHlLine >= 0 && savedHlLine < rows.size()) {
                    rows.get(savedHlLine).setHl(savedHl);
                    savedHl = null;
                }

                if (matchOffset != -1 && current >= 0 && current < numrows) {
                    EditorRow row = rows.get(current);
                    lastMatch = current;

                    if (row.getHl() != null) {
                        savedHlLine = current;
                        savedHl = row.getHl().clone();
                        int[] hl = row.getHl();
                        int qlen = query.length();
                        for (int k = 0; k < qlen && (matchOffset + k) < hl.length; k++) {
                            hl[matchOffset + k] = SyntaxHighlightDB.HL_MATCH;
                        }
                    }
                    cy = 0;
                    cx = matchOffset;
                    rowoff = current;
                    coloff = 0;
                    if (cx > screencols) {
                        int diff = cx - screencols;
                        cx -= diff;
                        coloff += diff;
                    }
                }
            }
        }
    }
}
