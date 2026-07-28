package com.kilo;

import java.io.BufferedReader;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

public class FileManager {

    public static boolean open(Editor editor, String filename) {
        editor.setFilename(filename);
        editor.setDirty(0);

        Path path = Paths.get(filename);
        if (!Files.exists(path)) {
            return true;
        }

        try (BufferedReader reader = Files.newBufferedReader(path, StandardCharsets.UTF_8)) {
            String line;
            while ((line = reader.readLine()) != null) {
                editor.insertRow(editor.getNumrows(), line);
            }
            editor.setDirty(0);
            return true;
        } catch (Exception e) {
            editor.setStatusMessage("Can't open file: %s", e.getMessage());
            return false;
        }
    }

    public static boolean save(Editor editor) {
        if (editor.getFilename() == null) {
            editor.setStatusMessage("No file name specified!");
            return false;
        }

        String buf = rowsToString(editor);
        byte[] bytes = buf.getBytes(StandardCharsets.UTF_8);

        try (FileOutputStream out = new FileOutputStream(editor.getFilename())) {
            out.write(bytes);
            out.flush();
            editor.setDirty(0);
            editor.setStatusMessage("%d bytes written on disk", bytes.length);
            return true;
        } catch (Exception e) {
            editor.setStatusMessage("Can't save! I/O error: %s", e.getMessage());
            return false;
        }
    }

    public static String rowsToString(Editor editor) {
        StringBuilder buf = new StringBuilder();
        for (EditorRow row : editor.getRows()) {
            buf.append(row.getChars()).append("\n");
        }
        return buf.toString();
    }
}
