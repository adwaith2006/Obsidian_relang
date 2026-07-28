//! Terminal management and drawing helper module.

use crossterm::{
    cursor::{Hide, MoveTo, Show},
    execute,
    style::{Color, ResetColor, SetBackgroundColor, SetForegroundColor},
    terminal::{disable_raw_mode, enable_raw_mode, Clear, ClearType},
    QueueableCommand,
};
use std::io::{stdout, Write};

pub struct TerminalGuard {
    pub raw: bool,
}

impl TerminalGuard {
    pub fn new(raw: bool) -> Self {
        if raw {
            let _ = enable_raw_mode();
            let _ = execute!(stdout(), Hide);
        }
        Self { raw }
    }

    pub fn restore(&self) {
        if self.raw {
            let _ = execute!(stdout(), Show, ResetColor);
            let _ = disable_raw_mode();
        }
    }
}

impl Drop for TerminalGuard {
    fn drop(&mut self) {
        self.restore();
    }
}

pub fn draw_round_box<W: Write>(
    out: &mut W,
    x: u16,
    y: u16,
    width: u16,
    height: u16,
    color: Option<Color>,
) -> std::io::Result<()> {
    if width < 2 || height < 2 {
        return Ok(());
    }

    if let Some(c) = color {
        out.queue(SetForegroundColor(c))?;
    }

    // Top line
    out.queue(MoveTo(x, y))?;
    write!(out, "╭{}╮", "─".repeat((width - 2) as usize))?;

    // Side lines
    for i in 1..(height - 1) {
        out.queue(MoveTo(x, y + i))?;
        write!(out, "│")?;
        out.queue(MoveTo(x + width - 1, y + i))?;
        write!(out, "│")?;
    }

    // Bottom line
    out.queue(MoveTo(x, y + height - 1))?;
    write!(out, "╰{}╯", "─".repeat((width - 2) as usize))?;

    if color.is_some() {
        out.queue(ResetColor)?;
    }

    Ok(())
}

pub fn clear_screen<W: Write>(out: &mut W, black_bg: bool) -> std::io::Result<()> {
    if black_bg {
        out.queue(SetBackgroundColor(Color::Black))?;
    } else {
        out.queue(ResetColor)?;
    }
    out.queue(Clear(ClearType::All))?;
    out.queue(MoveTo(0, 0))?;
    out.flush()
}
