//! Analog clock rendering module using half-block terminal characters.

use crossterm::{
    cursor::MoveTo,
    style::{Color, ResetColor, SetBackgroundColor, SetForegroundColor},
    QueueableCommand,
};
use std::collections::HashMap;
use std::io::Write;

#[derive(Hash, Eq, PartialEq, Clone, Copy)]
pub struct Point(pub i32, pub i32);

#[derive(Clone, Copy, PartialEq, Eq)]
pub struct RgbColor {
    pub r: u8,
    pub g: u8,
    pub b: u8,
}

impl RgbColor {
    pub const fn new(r: u8, g: u8, b: u8) -> Self {
        Self { r, g, b }
    }

    pub fn to_crossterm(self) -> Color {
        Color::Rgb {
            r: self.r,
            g: self.g,
            b: self.b,
        }
    }
}

pub type Pixels = HashMap<Point, RgbColor>;

pub fn rotate_from_12(theta: f64, radius: f64) -> (i32, i32) {
    (
        (-theta.sin() * radius).round() as i32,
        (-theta.cos() * radius).round() as i32,
    )
}

pub fn calculate_angle(max_v: f64, time_value: f64) -> f64 {
    2.0 * std::f64::consts::PI * (max_v - time_value) / max_v
}

pub fn angle_coords(max_v: f64, time_value: f64, radius: f64) -> (i32, i32) {
    rotate_from_12(calculate_angle(max_v, time_value), radius)
}

pub fn draw_line(pix: &mut Pixels, sx: i32, sy: i32, x0i: i32, y0i: i32, color: RgbColor) {
    let x1i = x0i + sx;
    let y0i = y0i * 2;
    let y1i = y0i + sy;

    let steep = (y1i - y0i).abs() > (x1i - x0i).abs();
    let (mut x0, mut y0, mut x1, mut y1) = if steep {
        (y0i, x0i, y1i, x1i)
    } else {
        (x0i, y0i, x1i, y1i)
    };

    if x0 > x1 {
        std::mem::swap(&mut x0, &mut x1);
        std::mem::swap(&mut y0, &mut y1);
    }

    let dx = x1 - x0;
    let dy = (y1 - y0).abs() as f64;
    let mut err = (dx as f64) / 2.0;
    let y_step = if y0 < y1 { 1 } else { -1 };

    let mut y = y0;
    for x in x0..=x1 {
        if steep {
            pix.insert(Point(y, x), color);
        } else {
            pix.insert(Point(x, y), color);
        }
        err -= dy;
        if err < 0.0 {
            y += y_step;
            err += dx as f64;
        }
    }
}

pub fn render_pixels<W: Write>(
    out: &mut W,
    mut pixels: Pixels,
    bg: RgbColor,
) -> std::io::Result<()> {
    let coords: Vec<Point> = pixels.keys().copied().collect();

    for pt in coords {
        if !pixels.contains_key(&pt) {
            continue;
        }
        let color = pixels.remove(&pt).unwrap();
        let x = pt.0;
        let y = pt.1;

        match y % 2 {
            0 => {
                out.queue(MoveTo(x.max(0) as u16, (y / 2).max(0) as u16))?;
                let lower = Point(x, y + 1);
                if let Some(&v) = pixels.get(&lower) {
                    if v == color {
                        out.queue(SetForegroundColor(color.to_crossterm()))?;
                        out.queue(SetBackgroundColor(color.to_crossterm()))?;
                        write!(out, "█")?;
                        pixels.remove(&lower);
                        continue;
                    }
                    out.queue(SetForegroundColor(v.to_crossterm()))?;
                    out.queue(SetBackgroundColor(color.to_crossterm()))?;
                    pixels.remove(&lower);
                } else {
                    out.queue(SetForegroundColor(bg.to_crossterm()))?;
                    out.queue(SetBackgroundColor(color.to_crossterm()))?;
                }
                write!(out, "▄")?;
            }
            _ => {
                let upper = Point(x, y - 1);
                if !pixels.contains_key(&upper) {
                    out.queue(MoveTo(x.max(0) as u16, (y / 2).max(0) as u16))?;
                    out.queue(SetForegroundColor(color.to_crossterm()))?;
                    out.queue(SetBackgroundColor(bg.to_crossterm()))?;
                    write!(out, "▄")?;
                }
            }
        }
    }
    out.queue(ResetColor)?;
    Ok(())
}

pub fn draw_analog_hands<W: Write>(
    out: &mut W,
    cx: i32,
    cy: i32,
    radius: i32,
    now: chrono::DateTime<chrono::Local>,
    seconds: bool,
    continuous: bool,
) -> std::io::Result<()> {
    use chrono::Timelike;

    let sec = if continuous {
        (now.nanosecond() as f64) / 1e9 + (now.second() as f64)
    } else {
        now.second() as f64
    };

    let r = radius as f64;
    let (sx, sy) = angle_coords(60.0, sec, 0.9 * r);
    let m = (now.minute() as f64) + sec / 60.0;
    let (mx, my) = angle_coords(60.0, m, 0.80 * r);
    let (hx, hy) = angle_coords(12.0, ((now.hour() % 12) as f64) + m / 60.0, 0.47 * r);

    let mut pix = Pixels::new();
    if seconds {
        draw_line(
            &mut pix,
            sx,
            sy,
            cx,
            cy,
            RgbColor::new(0x50, 0x80, 0x50),
        );
    }
    draw_line(
        &mut pix,
        mx,
        my,
        cx,
        cy,
        RgbColor::new(0x2C, 0x59, 0xD4),
    );
    draw_line(
        &mut pix,
        hx,
        hy,
        cx,
        cy,
        RgbColor::new(255, 167, 10),
    );

    let bg = RgbColor::new(0, 0, 0);
    render_pixels(out, pix, bg)?;

    out.queue(ResetColor)?;
    for n in 1..=60 {
        let (mut nx, ny) = angle_coords(60.0, (n % 60) as f64, r);
        let py = cy + (ny - 1) / 2;
        if n % 5 == 0 {
            let m = n / 5;
            if m >= 10 {
                nx -= 1;
            }
            let px = (cx + nx).max(0) as u16;
            out.queue(MoveTo(px, py.max(0) as u16))?;
            write!(out, "{}", m)?;
        } else if seconds {
            let px = (cx + nx).max(0) as u16;
            out.queue(MoveTo(px, py.max(0) as u16))?;
            write!(out, "•")?;
        }
    }

    Ok(())
}
