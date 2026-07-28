package com.kilo;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

public class SyntaxHighlightDB {
    public static final int HL_NORMAL = 0;
    public static final int HL_NONPRINT = 1;
    public static final int HL_COMMENT = 2;
    public static final int HL_MLCOMMENT = 3;
    public static final int HL_KEYWORD1 = 4;
    public static final int HL_KEYWORD2 = 5;
    public static final int HL_STRING = 6;
    public static final int HL_NUMBER = 7;
    public static final int HL_MATCH = 8;

    public static final int HL_HIGHLIGHT_STRINGS = 1 << 0;
    public static final int HL_HIGHLIGHT_NUMBERS = 1 << 1;

    private static final List<String> C_HL_EXTENSIONS = Arrays.asList(".c", ".h", ".cpp", ".hpp", ".cc");
    private static final List<String> C_HL_KEYWORDS = Arrays.asList(
            /* C Keywords */
            "auto", "break", "case", "continue", "default", "do", "else", "enum",
            "extern", "for", "goto", "if", "register", "return", "sizeof", "static",
            "struct", "switch", "typedef", "union", "volatile", "while", "NULL",

            /* C++ Keywords */
            "alignas", "alignof", "and", "and_eq", "asm", "bitand", "bitor", "class",
            "compl", "constexpr", "const_cast", "deltype", "delete", "dynamic_cast",
            "explicit", "export", "false", "friend", "inline", "mutable", "namespace",
            "new", "noexcept", "not", "not_eq", "nullptr", "operator", "or", "or_eq",
            "private", "protected", "public", "reinterpret_cast", "static_assert",
            "static_cast", "template", "this", "thread_local", "throw", "true", "try",
            "typeid", "typename", "virtual", "xor", "xor_eq",

            /* C types */
            "int|", "long|", "double|", "float|", "char|", "unsigned|", "signed|",
            "void|", "short|", "auto|", "const|", "bool|"
    );

    private static final List<EditorSyntax> HLDB = new ArrayList<>();

    static {
        HLDB.add(new EditorSyntax(
                C_HL_EXTENSIONS,
                C_HL_KEYWORDS,
                "//", "/*", "*/",
                HL_HIGHLIGHT_STRINGS | HL_HIGHLIGHT_NUMBERS
        ));
    }

    public static EditorSyntax selectSyntaxHighlight(String filename) {
        if (filename == null) {
            return null;
        }
        for (EditorSyntax s : HLDB) {
            for (String ext : s.getFilematch()) {
                int idx = filename.indexOf(ext);
                if (idx != -1) {
                    if (!ext.startsWith(".") || (idx + ext.length() == filename.length())) {
                        return s;
                    }
                }
            }
        }
        return null;
    }

    public static int syntaxToColor(int hl) {
        return switch (hl) {
            case HL_COMMENT, HL_MLCOMMENT -> 36; /* cyan */
            case HL_KEYWORD1 -> 33;            /* yellow */
            case HL_KEYWORD2 -> 32;            /* green */
            case HL_STRING -> 35;              /* magenta */
            case HL_NUMBER -> 31;              /* red */
            case HL_MATCH -> 34;               /* blue */
            default -> 37;                     /* white */
        };
    }
}
