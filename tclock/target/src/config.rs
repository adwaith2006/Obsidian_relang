//! CLI argument parsing and Configuration struct.

use clap::Parser;

#[derive(Parser, Debug, Clone)]
#[command(name = "tclock", about = "Terminal clock with analog/digital modes, countdown, and tailing")]
pub struct CliArgs {
    #[arg(short = '2', long = "24", help = "Use 24-hour time format")]
    pub twenty_four: bool,

    #[arg(long = "analog", help = "Analog clock with hours, minutes and seconds hands")]
    pub analog: bool,

    #[arg(long = "aa", help = "Use antialiased image based analog clock")]
    pub aa: bool,

    #[arg(short = 'c', help = "Analog clock updates continuously instead of seconds ticks")]
    pub continuous: bool,

    #[arg(long = "box", help = "Draw a simple rounded corner outline around the time")]
    pub box_outline: bool,

    #[arg(long = "color", default_value = "red", help = "Color to use (e.g., red, green, blue, yellow, #RRGGBB)")]
    pub color: String,

    #[arg(long = "color-box", default_value = "", help = "Color box around the time")]
    pub color_box: String,

    #[arg(long = "color-disc", default_value = "E0C020", help = "Color disc around the time")]
    pub color_disc: String,

    #[arg(long = "radius", default_value = "1.2", help = "Radius of disc around time")]
    pub radius: f64,

    #[arg(long = "black-bg", help = "Set a black background instead of using terminal background")]
    pub black_bg: bool,

    #[arg(long = "breath", help = "Pulse the color")]
    pub breath: bool,

    #[arg(long = "inverse", help = "Inverse foreground and background colors")]
    pub inverse: bool,

    #[arg(long = "no-seconds", help = "Don't show seconds")]
    pub no_seconds: bool,

    #[arg(long = "no-blink", help = "Don't blink the colon")]
    pub no_blink: bool,

    #[arg(long = "countdown", help = "Countdown duration (e.g. 5m, 10s, 1h)")]
    pub countdown: Option<String>,

    #[arg(long = "until", help = "Countdown until specific date/time (YYYY-MM-DD HH:MM:SS)")]
    pub until: Option<String>,

    #[arg(long = "text", help = "Text to display below the clock")]
    pub text: Option<String>,

    #[arg(long = "tail", help = "Tail the given filename while showing clock, or - for stdin")]
    pub tail: Option<String>,

    #[arg(long = "bounce", default_value = "0", help = "Bounce speed (0 is no bounce)")]
    pub bounce_speed: usize,

    #[arg(long = "fps", default_value = "30", help = "Maximum frames per second")]
    pub fps: f64,

    #[arg(help = "Optional raw digits or '-' for stdin tailing")]
    pub positional_arg: Option<String>,
}

#[derive(Clone, Debug)]
pub struct Config {
    pub boxed: bool,
    pub color: String,
    pub color_box: String,
    pub color_disc: Option<crossterm::style::Color>,
    pub analog: bool,
    pub aa: bool,
    pub continuous: bool,
    pub inverse: bool,
    pub breath: bool,
    pub radius: f64,
    pub black_bg: bool,
    pub seconds: bool,
    pub blink_enabled: bool,
    pub twenty_four: bool,
    pub format_str: String,
    pub text: String,
    pub tail: Option<String>,
    pub top_right: bool,
    pub bounce_speed: usize,
    pub bounce_cnt: usize,
    pub frame: usize,
    pub countdown_end: Option<chrono::DateTime<chrono::Local>>,
    pub is_countdown: bool,
}

pub fn parse_color(c: &str) -> crossterm::style::Color {
    use crossterm::style::Color;
    match c.to_lowercase().as_str() {
        "red" => Color::Red,
        "green" => Color::Green,
        "blue" => Color::Blue,
        "yellow" => Color::Yellow,
        "cyan" => Color::Cyan,
        "magenta" => Color::Magenta,
        "white" => Color::White,
        "black" => Color::Black,
        s if s.starts_with('#') && s.len() == 7 => {
            let r = u8::from_str_radix(&s[1..3], 16).unwrap_or(255);
            let g = u8::from_str_radix(&s[3..5], 16).unwrap_or(0);
            let b = u8::from_str_radix(&s[5..7], 16).unwrap_or(0);
            Color::Rgb { r, g, b }
        }
        s if s.len() == 6 => {
            let r = u8::from_str_radix(&s[0..2], 16).unwrap_or(255);
            let g = u8::from_str_radix(&s[2..4], 16).unwrap_or(0);
            let b = u8::from_str_radix(&s[4..6], 16).unwrap_or(0);
            Color::Rgb { r, g, b }
        }
        _ => Color::Red,
    }
}

pub fn parse_duration(s: &str) -> Option<chrono::Duration> {
    let s = s.trim();
    if s.is_empty() {
        return None;
    }
    let (num_part, unit_part) = s.split_at(s.find(|c: char| !c.is_numeric()).unwrap_or(s.len()));
    let val: i64 = num_part.parse().ok()?;

    match unit_part {
        "s" | "sec" | "seconds" => Some(chrono::Duration::seconds(val)),
        "m" | "min" | "minutes" => Some(chrono::Duration::minutes(val)),
        "h" | "hr" | "hours" => Some(chrono::Duration::hours(val)),
        "d" | "days" => Some(chrono::Duration::days(val)),
        "" => Some(chrono::Duration::seconds(val)),
        _ => None,
    }
}
