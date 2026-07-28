package com.kilo;

import java.util.Arrays;
import java.util.List;

public class EditorRow {
    private int idx;
    private StringBuilder chars;
    private String render;
    private int[] hl;
    private boolean hlOpenComment;

    public EditorRow(int idx, String text) {
        this.idx = idx;
        this.chars = new StringBuilder(text != null ? text : "");
        this.render = "";
        this.hl = new int[0];
        this.hlOpenComment = false;
    }

    public int getIdx() {
        return idx;
    }

    public void setIdx(int idx) {
        this.idx = idx;
    }

    public StringBuilder getChars() {
        return chars;
    }

    public int size() {
        return chars.length();
    }

    public String getRender() {
        return render;
    }

    public int getRsize() {
        return render != null ? render.length() : 0;
    }

    public int[] getHl() {
        return hl;
    }

    public void setHl(int[] hl) {
        this.hl = hl;
    }

    public boolean isHlOpenComment() {
        return hlOpenComment;
    }

    public static boolean isSeparator(char c) {
        return c == 0 || Character.isWhitespace(c) || ",.()+-/*=~%[];".indexOf(c) != -1;
    }

    public boolean hasOpenComment(String multilineCommentEnd) {
        if (hl != null && render != null && render.length() > 0 && hl.length > 0) {
            if (hl[hl.length - 1] == SyntaxHighlightDB.HL_MLCOMMENT) {
                if (multilineCommentEnd != null && multilineCommentEnd.length() >= 2) {
                    char e0 = multilineCommentEnd.charAt(0);
                    char e1 = multilineCommentEnd.charAt(1);
                    int rsize = render.length();
                    if (rsize < 2 || render.charAt(rsize - 2) != e0 || render.charAt(rsize - 1) != e1) {
                        return true;
                    }
                } else {
                    return true;
                }
            }
        }
        return false;
    }

    public void updateRow(EditorSyntax syntax, EditorRow prevRow) {
        StringBuilder r = new StringBuilder();
        for (int j = 0; j < chars.length(); j++) {
            char c = chars.charAt(j);
            if (c == KeyAction.TAB) {
                r.append(' ');
                while (r.length() % 8 != 0) {
                    r.append(' ');
                }
            } else {
                r.append(c);
            }
        }
        this.render = r.toString();
        updateSyntax(syntax, prevRow);
    }

    public boolean updateSyntax(EditorSyntax syntax, EditorRow prevRow) {
        int rlen = render.length();
        hl = new int[rlen];
        Arrays.fill(hl, SyntaxHighlightDB.HL_NORMAL);

        if (syntax == null) {
            boolean oldOc = hlOpenComment;
            hlOpenComment = false;
            return oldOc != hlOpenComment;
        }

        List<String> keywords = syntax.getKeywords();
        String scs = syntax.getSinglelineCommentStart();
        String mcs = syntax.getMultilineCommentStart();
        String mce = syntax.getMultilineCommentEnd();

        boolean hasScs = (scs != null && scs.length() >= 2);
        boolean hasMcs = (mcs != null && mcs.length() >= 2);
        boolean hasMce = (mce != null && mce.length() >= 2);

        boolean prevSep = true;
        char inString = 0;
        boolean inComment = (prevRow != null && prevRow.hasOpenComment(mce));

        int i = 0;
        while (i < rlen) {
            char c = render.charAt(i);

            /* Single-line comment */
            if (prevSep && hasScs && !inComment && inString == 0) {
                if (c == scs.charAt(0) && i + 1 < rlen && render.charAt(i + 1) == scs.charAt(1)) {
                    for (int j = i; j < rlen; j++) {
                        hl[j] = SyntaxHighlightDB.HL_COMMENT;
                    }
                    break;
                }
            }

            /* Multi-line comment */
            if (inComment) {
                hl[i] = SyntaxHighlightDB.HL_MLCOMMENT;
                if (hasMce && c == mce.charAt(0) && i + 1 < rlen && render.charAt(i + 1) == mce.charAt(1)) {
                    hl[i + 1] = SyntaxHighlightDB.HL_MLCOMMENT;
                    i += 2;
                    inComment = false;
                    prevSep = true;
                    continue;
                } else {
                    prevSep = false;
                    i++;
                    continue;
                }
            } else if (hasMcs && inString == 0 && c == mcs.charAt(0) && i + 1 < rlen && render.charAt(i + 1) == mcs.charAt(1)) {
                hl[i] = SyntaxHighlightDB.HL_MLCOMMENT;
                hl[i + 1] = SyntaxHighlightDB.HL_MLCOMMENT;
                i += 2;
                inComment = true;
                prevSep = false;
                continue;
            }

            /* Strings */
            if (inString != 0) {
                hl[i] = SyntaxHighlightDB.HL_STRING;
                if (c == '\\' && i + 1 < rlen) {
                    hl[i + 1] = SyntaxHighlightDB.HL_STRING;
                    i += 2;
                    prevSep = false;
                    continue;
                }
                if (c == inString) {
                    inString = 0;
                }
                i++;
                prevSep = false;
                continue;
            } else {
                if ((syntax.getFlags() & SyntaxHighlightDB.HL_HIGHLIGHT_STRINGS) != 0) {
                    if (c == '"' || c == '\'') {
                        inString = c;
                        hl[i] = SyntaxHighlightDB.HL_STRING;
                        i++;
                        prevSep = false;
                        continue;
                    }
                }
            }

            /* Non-printable characters */
            if (c < 32 || c >= 127) {
                hl[i] = SyntaxHighlightDB.HL_NONPRINT;
                i++;
                prevSep = false;
                continue;
            }

            /* Numbers */
            if ((syntax.getFlags() & SyntaxHighlightDB.HL_HIGHLIGHT_NUMBERS) != 0) {
                if ((Character.isDigit(c) && (prevSep || (i > 0 && hl[i - 1] == SyntaxHighlightDB.HL_NUMBER))) ||
                        (c == '.' && i > 0 && hl[i - 1] == SyntaxHighlightDB.HL_NUMBER)) {
                    hl[i] = SyntaxHighlightDB.HL_NUMBER;
                    i++;
                    prevSep = false;
                    continue;
                }
            }

            /* Keywords */
            if (prevSep && keywords != null) {
                boolean matched = false;
                for (String kw : keywords) {
                    boolean kw2 = kw.endsWith("|");
                    int klen = kw2 ? kw.length() - 1 : kw.length();
                    String kwTarget = kw2 ? kw.substring(0, klen) : kw;

                    if (i + klen <= rlen && render.startsWith(kwTarget, i)) {
                        char nextChar = (i + klen < rlen) ? render.charAt(i + klen) : '\0';
                        if (isSeparator(nextChar)) {
                            int hlType = kw2 ? SyntaxHighlightDB.HL_KEYWORD2 : SyntaxHighlightDB.HL_KEYWORD1;
                            for (int k = 0; k < klen; k++) {
                                hl[i + k] = hlType;
                            }
                            i += klen;
                            prevSep = false;
                            matched = true;
                            break;
                        }
                    }
                }
                if (matched) {
                    continue;
                }
            }

            prevSep = isSeparator(c);
            i++;
        }

        boolean newOc = hasOpenComment(mce);
        boolean changed = (hlOpenComment != newOc);
        hlOpenComment = newOc;
        return changed;
    }

    public void insertChar(int at, int c, EditorSyntax syntax, EditorRow prevRow) {
        if (at < 0 || at > chars.length()) {
            int padlen = at - chars.length();
            for (int i = 0; i < padlen; i++) {
                chars.append(' ');
            }
            chars.append((char) c);
        } else {
            chars.insert(at, (char) c);
        }
        updateRow(syntax, prevRow);
    }

    public void appendString(String s, EditorSyntax syntax, EditorRow prevRow) {
        if (s != null) {
            chars.append(s);
        }
        updateRow(syntax, prevRow);
    }

    public void delChar(int at, EditorSyntax syntax, EditorRow prevRow) {
        if (at >= 0 && at < chars.length()) {
            chars.deleteCharAt(at);
            updateRow(syntax, prevRow);
        }
    }
}
