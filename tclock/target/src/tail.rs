//! File and Stdin tailing module anchored to terminal top-right.

use crate::bignum::time_string;
use crate::config::Config;
use crossterm::{
    cursor::{MoveTo, RestorePosition, SavePosition},
    style::{ResetColor, SetForegroundColor},
    QueueableCommand,
};
use std::io::{self, BufReader, Read, Write};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::Duration;

pub fn run_tail<R: Read>(
    cfg: &mut Config,
    mut reader: BufReader<R>,
    running: Arc<AtomicBool>,
) -> io::Result<()> {
    let mut out = io::stdout();
    let mut prev_time_str = String::new();
    let mut blink = false;

    let mut buf = [0u8; 4096];

    while running.load(Ordering::Relaxed) {
        let now = chrono::Local::now();
        let num_str = if cfg.is_countdown {
            if let Some(end) = cfg.countdown_end {
                let dur = end.signed_duration_since(now);
                if dur.num_seconds() <= 0 {
                    out.queue(MoveTo(0, 24))?;
                    writeln!(out, "\n\n\x07Time's up reached at {}", now.format(&cfg.format_str))?;
                    out.flush()?;
                    return Ok(());
                }
                format_duration(dur, cfg.seconds)
            } else {
                now.format(&cfg.format_str).to_string()
            }
        } else {
            now.format(&cfg.format_str).to_string()
        };

        let mut do_draw = false;
        if num_str != prev_time_str {
            prev_time_str = num_str.clone();
            if cfg.blink_enabled {
                blink = !blink;
            }
            do_draw = true;
        }

        // Try non-blocking read
        let n = match reader.read(&mut buf) {
            Ok(n) => n,
            Err(e) if e.kind() == io::ErrorKind::WouldBlock => 0,
            Err(e) => return Err(e),
        };

        if n > 0 || do_draw {
            if n > 0 {
                out.write_all(&buf[..n])?;
                out.queue(SavePosition)?;
            }

            // Draw clock anchored at top right
            let formatted_time = time_string(&num_str, blink);
            let (term_w, _) = crossterm::terminal::size().unwrap_or((80, 24));
            let lines: Vec<&str> = formatted_time.lines().collect();
            let clock_w = lines.first().map(|l| l.chars().count()).unwrap_or(20) as u16;

            let start_x = term_w.saturating_sub(clock_w);

            for (i, line) in lines.iter().enumerate() {
                out.queue(MoveTo(start_x, i as u16))?;
                out.queue(SetForegroundColor(crate::config::parse_color(&cfg.color)))?;
                write!(out, "{}", line)?;
                out.queue(ResetColor)?;
            }

            if n > 0 {
                out.queue(RestorePosition)?;
            }
            out.flush()?;
        }

        std::thread::sleep(Duration::from_millis(50));
    }

    Ok(())
}

fn format_duration(dur: chrono::Duration, with_seconds: bool) -> String {
    let secs = dur.num_seconds().max(0);
    let days = secs / 86400;
    let hours = (secs % 86400) / 3600;
    let mins = (secs % 3600) / 60;
    let seconds = secs % 60;

    if days > 0 {
        if with_seconds {
            format!("{:02}:{:02}:{:02}:{:02}", days, hours, mins, seconds)
        } else {
            format!("{:02}:{:02}:{:02}", days, hours, mins)
        }
    } else if hours > 0 {
        if with_seconds {
            format!("{:02}:{:02}:{:02}", hours, mins, seconds)
        } else {
            format!("{:02}:{:02}", hours, mins)
        }
    } else {
        if with_seconds {
            format!("{:02}:{:02}", mins, seconds)
        } else {
            format!("{:02}", mins)
        }
    }
}
