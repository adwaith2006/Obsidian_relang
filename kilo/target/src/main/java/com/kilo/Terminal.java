package com.kilo;

import java.io.InputStream;

public class Terminal {
    private boolean rawMode = false;
    private final Thread shutdownHook;

    public Terminal() {
        this.shutdownHook = new Thread(this::disableRawMode);
        Runtime.getRuntime().addShutdownHook(shutdownHook);
    }

    public void enableRawMode() {
        if (rawMode) {
            return;
        }
        try {
            ProcessBuilder pb = new ProcessBuilder("stty", "raw", "-echo", "-ixon", "min", "1", "time", "0");
            pb.inheritIO();
            Process p = pb.start();
            if (p.waitFor() == 0) {
                rawMode = true;
                return;
            }
        } catch (Exception ignored) {}

        try {
            ProcessBuilder pb = new ProcessBuilder("sh", "-c", "stty raw -echo -ixon min 1 time 0 < /dev/tty");
            pb.inheritIO();
            Process p = pb.start();
            if (p.waitFor() == 0) {
                rawMode = true;
                return;
            }
        } catch (Exception ignored) {}

        try {
            ProcessBuilder pb = new ProcessBuilder("stty", "-F", "/dev/tty", "raw", "-echo", "-ixon");
            pb.inheritIO();
            Process p = pb.start();
            if (p.waitFor() == 0) {
                rawMode = true;
                return;
            }
        } catch (Exception ignored) {}

        /* Windows fallback */
        if (System.getProperty("os.name", "").toLowerCase().contains("win")) {
            try {
                ProcessBuilder pb = new ProcessBuilder("cmd", "/c", "mode con: cols=80 lines=25");
                pb.inheritIO();
                pb.start().waitFor();
            } catch (Exception ignored) {}
        }
        rawMode = true;
    }

    public void disableRawMode() {
        if (!rawMode) {
            return;
        }
        try {
            ProcessBuilder pb = new ProcessBuilder("stty", "sane");
            pb.inheritIO();
            Process p = pb.start();
            p.waitFor();
        } catch (Exception e) {
            try {
                ProcessBuilder pb = new ProcessBuilder("sh", "-c", "stty sane < /dev/tty");
                pb.inheritIO();
                Process p = pb.start();
                p.waitFor();
            } catch (Exception ignored) {}
        } finally {
            rawMode = false;
        }
    }

    public int readKey() {
        try {
            InputStream in = System.in;
            int c = in.read();
            if (c == -1) {
                System.exit(0);
            }

            if (c == KeyAction.ESC) {
                long start = System.currentTimeMillis();
                while (in.available() == 0 && (System.currentTimeMillis() - start) < 50) {
                    try {
                        Thread.sleep(5);
                    } catch (Exception ignored) {}
                }

                if (in.available() == 0) {
                    return KeyAction.ESC;
                }

                int seq0 = in.read();
                if (seq0 == -1) {
                    return KeyAction.ESC;
                }

                long start2 = System.currentTimeMillis();
                while (in.available() == 0 && (System.currentTimeMillis() - start2) < 50) {
                    try {
                        Thread.sleep(5);
                    } catch (Exception ignored) {}
                }

                if (in.available() == 0 && seq0 != '[' && seq0 != 'O') {
                    return KeyAction.ESC;
                }

                int seq1 = in.read();
                if (seq1 == -1) {
                    return KeyAction.ESC;
                }

                if (seq0 == '[') {
                    if (seq1 >= '0' && seq1 <= '9') {
                        long start3 = System.currentTimeMillis();
                        while (in.available() == 0 && (System.currentTimeMillis() - start3) < 50) {
                            try {
                                Thread.sleep(5);
                            } catch (Exception ignored) {}
                        }
                        if (in.available() == 0) {
                            return KeyAction.ESC;
                        }

                        int seq2 = in.read();
                        if (seq2 == '~') {
                            return switch (seq1) {
                                case '1', '7' -> KeyAction.HOME_KEY;
                                case '3', '8' -> KeyAction.DEL_KEY;
                                case '4' -> KeyAction.END_KEY;
                                case '5' -> KeyAction.PAGE_UP;
                                case '6' -> KeyAction.PAGE_DOWN;
                                default -> KeyAction.ESC;
                            };
                        }
                    } else {
                        return switch (seq1) {
                            case 'A' -> KeyAction.ARROW_UP;
                            case 'B' -> KeyAction.ARROW_DOWN;
                            case 'C' -> KeyAction.ARROW_RIGHT;
                            case 'D' -> KeyAction.ARROW_LEFT;
                            case 'H' -> KeyAction.HOME_KEY;
                            case 'F' -> KeyAction.END_KEY;
                            default -> KeyAction.ESC;
                        };
                    }
                } else if (seq0 == 'O') {
                    return switch (seq1) {
                        case 'H' -> KeyAction.HOME_KEY;
                        case 'F' -> KeyAction.END_KEY;
                        default -> KeyAction.ESC;
                    };
                }
                return KeyAction.ESC;
            }

            return c;
        } catch (Exception e) {
            return KeyAction.KEY_NULL;
        }
    }

    public void updateWindowSize(Editor editor) {
        int rows = 24;
        int cols = 80;

        try {
            ProcessBuilder pb = new ProcessBuilder("sh", "-c", "stty size < /dev/tty");
            Process p = pb.start();
            String output = new String(p.getInputStream().readAllBytes()).trim();
            p.waitFor();

            if (output.isEmpty()) {
                ProcessBuilder pb2 = new ProcessBuilder("stty", "size");
                Process p2 = pb2.start();
                output = new String(p2.getInputStream().readAllBytes()).trim();
                p2.waitFor();
            }

            if (!output.isEmpty()) {
                String[] parts = output.split("\\s+");
                if (parts.length >= 2) {
                    rows = Integer.parseInt(parts[0]);
                    cols = Integer.parseInt(parts[1]);
                }
            }
        } catch (Exception e) {
            int[] res = getWindowSizeVT100();
            if (res != null) {
                rows = res[0];
                cols = res[1];
            }
        }

        editor.setScreenrows(Math.max(1, rows - 2));
        editor.setScreencols(Math.max(1, cols));
    }

    private int[] getWindowSizeVT100() {
        try {
            System.out.print("\u001b[999C\u001b[999B\u001b[6n");
            System.out.flush();

            StringBuilder sb = new StringBuilder();
            InputStream in = System.in;
            long start = System.currentTimeMillis();

            while ((System.currentTimeMillis() - start) < 500) {
                if (in.available() > 0) {
                    int c = in.read();
                    if (c == 'R') {
                        sb.append((char) c);
                        break;
                    }
                    sb.append((char) c);
                } else {
                    Thread.sleep(10);
                }
            }

            String s = sb.toString();
            if (s.startsWith("\u001b[") && s.endsWith("R")) {
                String sub = s.substring(2, s.length() - 1);
                String[] parts = sub.split(";");
                if (parts.length == 2) {
                    int r = Integer.parseInt(parts[0]);
                    int c = Integer.parseInt(parts[1]);
                    return new int[]{r, c};
                }
            }
        } catch (Exception ignored) {}
        return null;
    }
}
