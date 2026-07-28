//! tclock — Terminal clock in Rust with analog/digital modes, countdown, and tailing.

mod analog;
mod bignum;
mod config;
mod image_clock;
mod tail;
mod term;

use crate::bignum::time_string;
use crate::config::{parse_color, parse_duration, CliArgs, Config};
use crate::term::{clear_screen, draw_round_box, TerminalGuard};
use clap::Parser;
use crossterm::{
    cursor::MoveTo,
    event::{self, Event, KeyCode, KeyModifiers, MouseButton, MouseEventKind},
    style::{ResetColor, SetForegroundColor},
    terminal::size as term_size,
    QueueableCommand,
};
use std::io::{stdin, stdout, BufReader, Write};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::{Duration, Instant};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = CliArgs::parse();

    // Check positional argument
    if let Some(ref arg) = args.positional_arg {
        if arg == "-" {
            // Stdin tail mode
            let running = Arc::new(AtomicBool::new(true));
            let r = running.clone();
            ctrlc_handler(r);

            let mut cfg = build_config(&args);
            cfg.top_right = true;
            cfg.boxed = true;
            let reader = BufReader::new(stdin());
            return tail::run_tail(&mut cfg, reader, running).map_err(|e| e.into());
        } else if !arg.is_empty() && arg.chars().all(|c| c.is_ascii_digit() || c == ':') {
            // Single print digits mode (matching Go TimeString argument)
            println!("{}", time_string(arg, false));
            return Ok(());
        }
    }

    // Tail file mode
    if let Some(ref path) = args.tail {
        let mut cfg = build_config(&args);
        cfg.top_right = true;
        cfg.boxed = true;
        let running = Arc::new(AtomicBool::new(true));
        ctrlc_handler(running.clone());

        if path == "-" {
            let reader = BufReader::new(stdin());
            return tail::run_tail(&mut cfg, reader, running).map_err(|e| e.into());
        } else {
            let file = std::fs::File::open(path)?;
            let reader = BufReader::new(file);
            return tail::run_tail(&mut cfg, reader, running).map_err(|e| e.into());
        }
    }

    // Interactive Terminal Loop
    let guard = TerminalGuard::new(true);
    let mut out = stdout();

    let mut cfg = build_config(&args);
    clear_screen(&mut out, cfg.black_bg)?;

    let frame_dur = Duration::from_micros((1_000_000.0 / cfg_fps(&args)).max(1.0) as u64);
    let mut prev_time_str = String::new();
    let mut blink = false;
    let mut mouse_x: u16 = 0;
    let mut mouse_y: u16 = 0;
    let mut track_mouse = false;

    while !EXIT_FLAG.load(Ordering::Relaxed) {
        let frame_start = Instant::now();

        // Check crossterm input events
        while event::poll(Duration::from_millis(0))? {
            match event::read()? {
                Event::Key(key) => match key.code {
                    KeyCode::Char('q') | KeyCode::Char('Q') => {
                        return Ok(());
                    }
                    KeyCode::Char('c') if key.modifiers.contains(KeyModifiers::CONTROL) => {
                        return Ok(());
                    }
                    KeyCode::Char('a') | KeyCode::Char('A') => {
                        cfg.aa = !cfg.aa;
                        cfg.analog = !cfg.aa;
                        clear_screen(&mut out, cfg.black_bg)?;
                    }
                    KeyCode::Char('c') | KeyCode::Char('C') => {
                        cfg.continuous = !cfg.continuous;
                    }
                    _ => {}
                },
                Event::Mouse(mouse) => {
                    mouse_x = mouse.column;
                    mouse_y = mouse.row;
                    if mouse.kind == MouseEventKind::Down(MouseButton::Left) {
                        track_mouse = !track_mouse;
                    }
                }
                Event::Resize(_, _) => {
                    clear_screen(&mut out, cfg.black_bg)?;
                }
                _ => {}
            }
        }

        let now = chrono::Local::now();
        let num_str = if cfg.is_countdown {
            if let Some(end) = cfg.countdown_end {
                let dur = end.signed_duration_since(now);
                if dur.num_seconds() <= 0 {
                    out.queue(MoveTo(0, 20))?;
                    writeln!(out, "\x07Time's up reached at {}", now.format(&cfg.format_str))?;
                    out.flush()?;
                    std::thread::sleep(Duration::from_secs(2));
                    return Ok(());
                }
                format_countdown(dur, cfg.seconds)
            } else {
                now.format(&cfg.format_str).to_string()
            }
        } else {
            now.format(&cfg.format_str).to_string()
        };

        if num_str != prev_time_str {
            prev_time_str = num_str.clone();
            if cfg.blink_enabled {
                blink = !blink;
            }
        }

        clear_screen(&mut out, cfg.black_bg)?;

        let (tw, th) = term_size().unwrap_or((80, 24));

        if cfg.aa {
            image_clock::draw_aa_analog_clock(
                &mut out,
                tw as usize,
                th as usize,
                now,
                cfg.seconds,
                cfg.continuous,
            )?;
        } else if cfg.analog {
            let radius = (tw / 2).min(th) as i32 - 1;
            analog::draw_analog_hands(
                &mut out,
                (tw / 2) as i32,
                (th / 2) as i32,
                radius,
                now,
                cfg.seconds,
                cfg.continuous,
            )?;
        } else {
            let formatted = time_string(&num_str, blink);
            let lines: Vec<&str> = formatted.lines().collect();

            let mut w = lines.first().map(|l| l.chars().count()).unwrap_or(20) as u16;
            let mut h = lines.len() as u16;

            if cfg.boxed {
                w += 2;
                h += 2;
            }

            let (cx, cy) = if track_mouse {
                (mouse_x.saturating_sub(w / 2), mouse_y.saturating_sub(h / 2))
            } else {
                (tw.saturating_sub(w) / 2, th.saturating_sub(h) / 2)
            };

            if cfg.boxed {
                let box_color = if !cfg.color_box.is_empty() {
                    Some(parse_color(&cfg.color_box))
                } else {
                    Some(parse_color(&cfg.color))
                };
                draw_round_box(&mut out, cx, cy, w, h, box_color)?;
            }

            let text_x = if cfg.boxed { cx + 1 } else { cx };
            let text_y = if cfg.boxed { cy + 1 } else { cy };

            out.queue(SetForegroundColor(parse_color(&cfg.color)))?;
            for (i, line) in lines.iter().enumerate() {
                out.queue(MoveTo(text_x, text_y + (i as u16)))?;
                write!(out, "{}", line)?;
            }
            out.queue(ResetColor)?;

            if !cfg.text.is_empty() {
                let txt_w = cfg.text.chars().count() as u16;
                let txt_x = cx + w / 2 - txt_w / 2;
                out.queue(MoveTo(txt_x, cy + h + 1))?;
                write!(out, "{}", cfg.text)?;
            }
        }

        out.flush()?;

        let elapsed = frame_start.elapsed();
        if elapsed < frame_dur {
            std::thread::sleep(frame_dur - elapsed);
        }
    }

    drop(guard);
    Ok(())
}

static EXIT_FLAG: AtomicBool = AtomicBool::new(false);

fn ctrlc_handler(running: Arc<AtomicBool>) {
    let r = running.clone();
    ctrlc::set_handler(move || {
        r.store(false, Ordering::Relaxed);
        EXIT_FLAG.store(true, Ordering::Relaxed);
    })
    .ok();
}

fn cfg_fps(args: &CliArgs) -> f64 {
    args.fps.clamp(1.0, 100.0)
}

fn build_config(args: &CliArgs) -> Config {
    let format_str = if args.twenty_four {
        if args.no_seconds {
            "%H:%M".to_string()
        } else {
            "%H:%M:%S".to_string()
        }
    } else {
        if args.no_seconds {
            "%I:%M".to_string()
        } else {
            "%I:%M:%S".to_string()
        }
    };

    let mut is_countdown = false;
    let mut countdown_end = None;
    let now = chrono::Local::now();

    if let Some(ref dur_str) = args.countdown {
        if let Some(dur) = parse_duration(dur_str) {
            is_countdown = true;
            countdown_end = Some(now + dur);
        }
    } else if let Some(ref until_str) = args.until {
        if let Ok(naive) = chrono::NaiveDateTime::parse_from_str(until_str, "%Y-%m-%d %H:%M:%S") {
            if let Some(local_dt) = naive.and_local_timezone(chrono::Local).single() {
                is_countdown = true;
                countdown_end = Some(local_dt);
            }
        }
    }

    let text = args.text.clone().unwrap_or_default();

    Config {
        boxed: args.box_outline || !args.color_box.is_empty(),
        color: args.color.clone(),
        color_box: args.color_box.clone(),
        color_disc: Some(parse_color(&args.color_disc)),
        analog: args.analog,
        aa: args.aa,
        continuous: args.continuous,
        inverse: args.inverse,
        breath: args.breath,
        radius: args.radius,
        black_bg: args.black_bg,
        seconds: !args.no_seconds,
        blink_enabled: !args.no_blink,
        twenty_four: args.twenty_four,
        format_str,
        text,
        tail: args.tail.clone(),
        top_right: false,
        bounce_speed: args.bounce_speed,
        bounce_cnt: 0,
        frame: 0,
        countdown_end,
        is_countdown,
    }
}

fn format_countdown(dur: chrono::Duration, with_seconds: bool) -> String {
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
