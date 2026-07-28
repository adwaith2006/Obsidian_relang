package com.kilo;

import java.util.List;

public class EditorSyntax {
    private final List<String> filematch;
    private final List<String> keywords;
    private final String singlelineCommentStart;
    private final String multilineCommentStart;
    private final String multilineCommentEnd;
    private final int flags;

    public EditorSyntax(List<String> filematch,
                        List<String> keywords,
                        String singlelineCommentStart,
                        String multilineCommentStart,
                        String multilineCommentEnd,
                        int flags) {
        this.filematch = filematch;
        this.keywords = keywords;
        this.singlelineCommentStart = singlelineCommentStart;
        this.multilineCommentStart = multilineCommentStart;
        this.multilineCommentEnd = multilineCommentEnd;
        this.flags = flags;
    }

    public List<String> getFilematch() {
        return filematch;
    }

    public List<String> getKeywords() {
        return keywords;
    }

    public String getSinglelineCommentStart() {
        return singlelineCommentStart;
    }

    public String getMultilineCommentStart() {
        return multilineCommentStart;
    }

    public String getMultilineCommentEnd() {
        return multilineCommentEnd;
    }

    public int getFlags() {
        return flags;
    }
}
