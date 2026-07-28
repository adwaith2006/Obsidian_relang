/// pipes — animated Unicode box-drawing pipes terminal screensaver.
///
/// Faithful Rust port of the Python `pipes` reference implementation.
///
/// Direction encoding (matches Python source):
///   UP=0, RIGHT=1, DOWN=2, LEFT=3
///
/// Character index = pipe_type * 16 + old_direction * 4 + new_direction
///
/// Pipe sets: each 16-char string encodes all 4×4 direction combinations.
/// Layout per set:
///   [UP→UP, UP→R, UP→D, UP→L,
///    R→UP,  R→R,  R→D,  R→L,
///    D→UP,  D→R,  D→D,  D→L,
///    L→UP,  L→R,  L→D,  L→L]

use std::io::{self, Write};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::{Duration, Instant};

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/// All pipe character sets.  Each entry is exactly 16 Unicode scalars.
const PIPE_SETS: &[&str] = &[
    "┃┏ ┓┛━┓  ┗┃┛┗ ┏━",  // 0 HEAVY
    "│╭ ╮╯─╮  ╰│╯╰ ╭─",  // 1 CURVED
    "│┌ ┐┘─┐  └│┘└ ┌─",  // 2 LIGHT
    "║╔ ╗╝═╗  ╚║╝╚ ╔═",  // 3 DOUBLE
    "|+ ++-+  +|++ +-",  // 4 KNOBBY
    "|/ \\ /-\\  \\|/\\ /-",  // 5 ANGLES
    ".o ....  .... .o",  // 6 DOTS
    ".o oo.o  o.oo o.",  // 7 DOTS_O
    "-\\ /\\|/  /-\\/ \\|",  // 8 SLASHES
    "╿┍ ┑┚╼┒  ┕╽┙┖ ┎╾",  // 9 MIXED
];

/// ANSI foreground color codes for colors 0-7 (matches curses color indices).
const ANSI_COLORS: &[u8] = &[30, 31, 32, 33, 34, 35, 36, 37];

/// Default color cycle: curses colors 1-7 then 0.
const DEFAULT_COLORS: &[usize] = &[1, 2, 3, 4, 5, 6, 7, 0];

// ---------------------------------------------------------------------------
// Direction
// ---------------------------------------------------------------------------

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
#[repr(u8)]
enum Direction {
    Up    = 0,
    Right = 1,
    Down  = 2,
    Left  = 3,
}

impl Direction {
    fn from_u8(v: u8) -> Self {
        match v % 4 {
            0 => Direction::Up,
            1 => Direction::Right,
            2 => Direction::Down,
            _ => Direction::Left,
        }
    }

    fn as_u8(self) -> u8 {
        self as u8
    }
}

// ---------------------------------------------------------------------------
// Pipe character lookup
// ---------------------------------------------------------------------------

/// Collect each pipe set into a flat `Vec<char>` where `chars[set*16 + old*4 + new]`
/// gives the character for that (set, old_direction → new_direction) combination.
fn build_char_table(sets: &[&str]) -> Vec<char> {
    let mut table = Vec::new();
    for s in sets {
        let chars: Vec<char> = s.chars().collect();
        // Pad / truncate to exactly 16 chars.
        let mut row = [' '; 16];
        for (i, &c) in chars.iter().enumerate().take(16) {
            row[i] = c;
        }
        table.extend_from_slice(&row);
    }
    table
}

fn lookup_char(table: &[char], pipe_type: usize, old: Direction, new: Direction) -> char {
    let idx = pipe_type * 16 + old.as_u8() as usize * 4 + new.as_u8() as usize;
    table.get(idx).copied().unwrap_or('?')
}

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

struct Config {
    num_pipes:    usize,
    fps:          u64,
    steady:       u32,
    limit:        usize,
    random_start: bool,
    bold:         bool,
    color:        bool,
    keep_style:   bool,
    colors:       Vec<usize>,
    pipe_types:   Vec<usize>,
}

impl Default for Config {
    fn default() -> Self {
        Config {
            num_pipes:    1,
            fps:          75,
            steady:       13,
            limit:        2000,
            random_start: false,
            bold:         true,
            color:        true,
            keep_style:   false,
            colors:       DEFAULT_COLORS.to_vec(),
            pipe_types:   vec![0],
        }
    }
}

// ---------------------------------------------------------------------------
// Simple LCG random (no external crates needed)
// ---------------------------------------------------------------------------

struct Rng {
    state: u64,
}

impl Rng {
    fn new() -> Self {
        // Seed from current time.
        let seed = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_nanos() as u64)
            .unwrap_or(12345);
        Rng { state: seed ^ 0xdeadbeef_cafebabe }
    }

    fn next_u64(&mut self) -> u64 {
        // xorshift64
        self.state ^= self.state << 13;
        self.state ^= self.state >> 7;
        self.state ^= self.state << 17;
        self.state
    }

    fn rand_range(&mut self, n: u64) -> u64 {
        if n == 0 { return 0; }
        self.next_u64() % n
    }

    fn rand_bool(&mut self) -> bool {
        self.next_u64() & 1 == 0
    }
}

// ---------------------------------------------------------------------------
// Pipe state
// ---------------------------------------------------------------------------

struct Pipe {
    x:         i32,
    y:         i32,
    direction: Direction,
    pipe_type: usize,
    color:     usize,
}

// ---------------------------------------------------------------------------
// Terminal helpers
// ---------------------------------------------------------------------------

fn hide_cursor(out: &mut impl Write) {
    write!(out, "\x1b[?25l").ok();
}

fn show_cursor(out: &mut impl Write) {
    write!(out, "\x1b[?25h").ok();
    out.flush().ok();
}

fn move_cursor(out: &mut impl Write, x: i32, y: i32) {
    // ANSI: ESC[row;colH  (1-indexed)
    write!(out, "\x1b[{};{}H", y + 1, x + 1).ok();
}

fn set_color(out: &mut impl Write, color_idx: usize, bold: bool) {
    let ansi = ANSI_COLORS.get(color_idx % ANSI_COLORS.len()).copied().unwrap_or(37);
    if bold {
        write!(out, "\x1b[1;{}m", ansi).ok();
    } else {
        write!(out, "\x1b[0;{}m", ansi).ok();
    }
}

fn reset_color(out: &mut impl Write) {
    write!(out, "\x1b[0m").ok();
}

fn clear_screen(out: &mut impl Write) {
    write!(out, "\x1b[2J\x1b[H").ok();
}

/// Query terminal size using ANSI DSR / fallback to 80×24.
fn get_terminal_size() -> (u16, u16) {
    // Try ioctl on Linux/macOS via /proc or env var.
    if let Ok(cols) = std::env::var("COLUMNS") {
        if let Ok(rows) = std::env::var("LINES") {
            if let (Ok(c), Ok(r)) = (cols.parse::<u16>(), rows.parse::<u16>()) {
                if c > 0 && r > 0 {
                    return (c, r);
                }
            }
        }
    }

    // Try stty size.
    if let Ok(out) = std::process::Command::new("stty")
        .arg("size")
        .output()
    {
        let s = String::from_utf8_lossy(&out.stdout);
        let parts: Vec<&str> = s.trim().split_whitespace().collect();
        if parts.len() == 2 {
            if let (Ok(r), Ok(c)) = (parts[0].parse::<u16>(), parts[1].parse::<u16>()) {
                if r > 0 && c > 0 {
                    return (c, r);
                }
            }
        }
    }

    (80, 24)
}

// ---------------------------------------------------------------------------
// Main simulation
// ---------------------------------------------------------------------------

fn run(config: &Config, running: Arc<AtomicBool>) {
    let stdout = io::stdout();
    let mut out = io::BufWriter::new(stdout.lock());

    let char_table = build_char_table(PIPE_SETS);

    let mut rng = Rng::new();

    let (mut width, mut height) = get_terminal_size();

    hide_cursor(&mut out);
    clear_screen(&mut out);
    out.flush().ok();

    // Build initial pipes.
    let mut pipes: Vec<Pipe> = (0..config.num_pipes)
        .map(|_| {
            let direction = if config.random_start {
                Direction::from_u8(rng.rand_range(4) as u8)
            } else {
                Direction::Up
            };
            let x = if config.random_start {
                rng.rand_range(width as u64) as i32
            } else {
                width as i32 / 2
            };
            let y = if config.random_start {
                rng.rand_range(height as u64) as i32
            } else {
                height as i32 / 2
            };
            let pipe_type = config.pipe_types[rng.rand_range(config.pipe_types.len() as u64) as usize];
            let color     = config.colors[rng.rand_range(config.colors.len() as u64) as usize];

            Pipe { x, y, direction, pipe_type, color }
        })
        .collect();

    let frame_dur = Duration::from_micros(1_000_000 / config.fps.max(1));
    let mut count: usize = 0;

    while running.load(Ordering::Relaxed) {
        let frame_start = Instant::now();

        // Check terminal resize.
        let (new_w, new_h) = get_terminal_size();
        if new_w != width || new_h != height {
            width  = new_w;
            height = new_h;
            clear_screen(&mut out);
        }

        // Update every pipe.
        for pipe in pipes.iter_mut() {
            let old_dir = pipe.direction;

            // Move position based on current direction (matches Python logic):
            //   if direction is odd (RIGHT=1 or LEFT=3): x += -direction + 2
            //   if direction is even (UP=0 or DOWN=2):   y += direction - 1
            let (nx, ny) = match old_dir {
                Direction::Up    => (pipe.x,     pipe.y - 1),
                Direction::Right => (pipe.x + 1, pipe.y),
                Direction::Down  => (pipe.x,     pipe.y + 1),
                Direction::Left  => (pipe.x - 1, pipe.y),
            };

            // Wrap / reset style on boundary crossing.
            let mut x = nx;
            let mut y = ny;
            let wrapped = x < 0 || x >= width as i32 || y < 0 || y >= height as i32;
            if wrapped {
                if !config.keep_style {
                    pipe.pipe_type = config.pipe_types[rng.rand_range(config.pipe_types.len() as u64) as usize];
                    pipe.color     = config.colors[rng.rand_range(config.colors.len() as u64) as usize];
                }
                x = x.rem_euclid(width as i32);
                y = y.rem_euclid(height as i32);
            }

            // Maybe turn (matches Python: randrange(steady) <= 1).
            let new_dir = if rng.rand_range(config.steady as u64) <= 1 {
                let turn: i8 = if rng.rand_bool() { 1 } else { -1 };
                Direction::from_u8((old_dir.as_u8() as i8 + turn).rem_euclid(4) as u8)
            } else {
                old_dir
            };

            // Draw at the *current* position (before the step) with the
            // character that encodes the transition old→new.
            let ch = lookup_char(&char_table, pipe.pipe_type, old_dir, new_dir);
            move_cursor(&mut out, pipe.x, pipe.y);
            if config.color {
                set_color(&mut out, pipe.color, config.bold);
            } else if config.bold {
                write!(out, "\x1b[1m").ok();
            }
            write!(out, "{}", ch).ok();
            if config.color || config.bold {
                reset_color(&mut out);
            }

            // Commit new state.
            pipe.x         = x;
            pipe.y         = y;
            pipe.direction = new_dir;
        }

        out.flush().ok();

        count += pipes.len();
        if config.limit > 0 && count >= config.limit {
            clear_screen(&mut out);
            count = 0;
        }

        // Sleep for the remainder of the frame.
        let elapsed = frame_start.elapsed();
        if elapsed < frame_dur {
            std::thread::sleep(frame_dur - elapsed);
        }
    }

    // Restore terminal.
    reset_color(&mut out);
    clear_screen(&mut out);
    show_cursor(&mut out);
}

// ---------------------------------------------------------------------------
// CLI argument parsing (no clap dependency)
// ---------------------------------------------------------------------------

fn parse_args() -> Config {
    let mut cfg = Config::default();
    let args: Vec<String> = std::env::args().skip(1).collect();
    let mut i = 0;
    while i < args.len() {
        match args[i].as_str() {
            "-p" | "--pipes" => {
                if let Some(v) = args.get(i + 1) {
                    if let Ok(n) = v.parse::<usize>() { cfg.num_pipes = n.max(1); }
                    i += 1;
                }
            }
            "-f" | "--fps" => {
                if let Some(v) = args.get(i + 1) {
                    if let Ok(n) = v.parse::<u64>() { cfg.fps = n.clamp(20, 100); }
                    i += 1;
                }
            }
            "-s" | "--steady" => {
                if let Some(v) = args.get(i + 1) {
                    if let Ok(n) = v.parse::<u32>() { cfg.steady = n.clamp(3, 15); }
                    i += 1;
                }
            }
            "-r" | "--limit" => {
                if let Some(v) = args.get(i + 1) {
                    if let Ok(n) = v.parse::<usize>() { cfg.limit = n; }
                    i += 1;
                }
            }
            "-R" | "--random"     => { cfg.random_start = true; }
            "-B" | "--no-bold"    => { cfg.bold         = false; }
            "-C" | "--no-color"   => { cfg.color        = false; }
            "-K" | "--keep-style" => { cfg.keep_style   = true; }
            "-P" | "--pipe-style" => {
                if let Some(v) = args.get(i + 1) {
                    if let Ok(n) = v.parse::<usize>() {
                        cfg.pipe_types = vec![n % PIPE_SETS.len()];
                    }
                    i += 1;
                }
            }
            "-h" | "--help" => {
                println!("pipes-rs — animated Unicode pipes terminal screensaver");
                println!();
                println!("Usage: pipes [OPTIONS]");
                println!();
                println!("Options:");
                println!("  -p, --pipes <N>        Number of pipes (default: 1)");
                println!("  -f, --fps <N>          Frames per second, 20-100 (default: 75)");
                println!("  -s, --steady <N>       Steadiness, 3-15 (default: 13)");
                println!("  -r, --limit <N>        Characters before screen reset (default: 2000)");
                println!("  -R, --random           Random start positions and directions");
                println!("  -B, --no-bold          Disable bold text");
                println!("  -C, --no-color         Disable color");
                println!("  -K, --keep-style       Keep style on wrap");
                println!("  -P, --pipe-style <0-9> Pipe character style (default: 0)");
                println!("  -h, --help             Show this help");
                println!();
                println!("Styles:");
                println!("  0: heavy (┃━)   1: curved (│─╭╮╯╰)  2: light (│─┌┐┘└)");
                println!("  3: double (║═)  4: knobby (|+-+)     5: angles (|/-\\)");
                println!("  6: dots (.o)    7: dots_o (.o)        8: slashes (-\\/)");
                println!("  9: mixed (╿╼)");
                println!();
                println!("Press Ctrl-C to quit.");
                std::process::exit(0);
            }
            _ => {}
        }
        i += 1;
    }
    cfg
}

// ---------------------------------------------------------------------------
// Entry point
// ---------------------------------------------------------------------------

fn main() {
    let config = parse_args();

    // Set up Ctrl-C handler that sets a flag.
    let running = Arc::new(AtomicBool::new(true));
    let r = running.clone();

    // On SIGINT/SIGTERM restore the cursor before exiting.
    ctrlc_handler(r.clone());

    run(&config, running);

    // Ensure cursor is restored on normal exit too.
    let stdout = io::stdout();
    let mut out = io::BufWriter::new(stdout.lock());
    show_cursor(&mut out);
}

/// Install a Ctrl-C / SIGINT handler using a background thread polling stdin.
/// We use a simple approach: spawn a thread that blocks on stdin, and the
/// main thread checks the AtomicBool each frame.
///
/// For proper signal handling on Linux we use libc-free approach:
/// the `signal` crate is not available (no_std), so we write the handler
/// directly in a way that compiles on stable Rust with no external crates.
#[cfg(unix)]
fn ctrlc_handler(_running: Arc<AtomicBool>) {
    use std::os::raw::c_int;

    extern "C" fn handler(_sig: c_int) {
        // Restore cursor and reset color in signal context.
        // Use raw write(2) syscall — safe here since it's signal-async-signal-safe.
        let restore = b"\x1b[?25h\x1b[0m\n";
        unsafe {
            extern "C" {
                fn write(fd: c_int, buf: *const u8, count: usize) -> isize;
            }
            write(1, restore.as_ptr(), restore.len());
        }
        unsafe { libc_exit(0); }
    }

    unsafe fn libc_exit(code: c_int) -> ! {
        extern "C" { fn _exit(status: c_int) -> !; }
        _exit(code)
    }

    unsafe {
        extern "C" {
            fn signal(signum: c_int, handler: unsafe extern "C" fn(c_int)) -> unsafe extern "C" fn(c_int);
        }
        signal(2 /* SIGINT  */, handler as unsafe extern "C" fn(c_int));
        signal(15 /* SIGTERM */, handler as unsafe extern "C" fn(c_int));
    }
}

#[cfg(not(unix))]
fn ctrlc_handler(running: Arc<AtomicBool>) {
    // Windows: spawn a thread that listens and sets the flag.
    std::thread::spawn(move || {
        // Blocking read on stdin will unblock on Ctrl-C on Windows.
        let mut input = String::new();
        let _ = std::io::stdin().read_line(&mut input);
        running.store(false, Ordering::Relaxed);
    });
}
