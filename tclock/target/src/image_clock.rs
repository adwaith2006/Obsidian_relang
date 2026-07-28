//! Antialiased (AA) image-based analog clock module.

use crossterm::{
    cursor::MoveTo,
    style::{Color, ResetColor, SetBackgroundColor, SetForegroundColor},
    QueueableCommand,
};
use std::io::Write;

pub struct RgbaCanvas {
    pub width: usize,
    pub height: usize,
    pub data: Vec<[u8; 4]>,
}

impl RgbaCanvas {
    pub fn new(width: usize, height: usize) -> Self {
        Self {
            width,
            height,
            data: vec![[0, 0, 0, 0]; width * height],
        }
    }

    pub fn put_pixel(&mut self, x: i32, y: i32, color: [u8; 4], alpha_factor: f64) {
        if x < 0 || y < 0 || (x as usize) >= self.width || (y as usize) >= self.height {
            return;
        }
        let idx = (y as usize) * self.width + (x as usize);
        let a = ((color[3] as f64) * alpha_factor) as u8;
        if a == 0 {
            return;
        }
        let current = self.data[idx];
        if current[3] == 0 {
            self.data[idx] = [color[0], color[1], color[2], a];
        } else {
            // Simple alpha blending
            let fg_a = (a as f64) / 255.0;
            let bg_a = (current[3] as f64) / 255.0 * (1.0 - fg_a);
            let out_a = fg_a + bg_a;
            if out_a > 0.0 {
                let r = ((color[0] as f64) * fg_a + (current[0] as f64) * bg_a) / out_a;
                let g = ((color[1] as f64) * fg_a + (current[1] as f64) * bg_a) / out_a;
                let b = ((color[2] as f64) * fg_a + (current[2] as f64) * bg_a) / out_a;
                self.data[idx] = [r as u8, g as u8, b as u8, (out_a * 255.0) as u8];
            }
        }
    }

    pub fn draw_aa_line(&mut self, x0: f64, y0: f64, x1: f64, y1: f64, color: [u8; 4]) {
        let steep = (y1 - y0).abs() > (x1 - x0).abs();
        let (mut x0, mut y0, mut x1, mut y1) = if steep {
            (y0, x0, y1, x1)
        } else {
            (x0, y0, x1, y1)
        };

        if x0 > x1 {
            std::mem::swap(&mut x0, &mut x1);
            std::mem::swap(&mut y0, &mut y1);
        }

        let dx = x1 - x0;
        let dy = y1 - y0;
        let gradient = if dx == 0.0 { 1.0 } else { dy / dx };

        // Handle first endpoint
        let xend = x0.round();
        let yend = y0 + gradient * (xend - x0);
        let xgap = 1.0 - (x0 + 0.5).fract();
        let xpxl1 = xend as i32;
        let ypxl1 = yend.floor() as i32;

        if steep {
            self.put_pixel(ypxl1, xpxl1, color, (1.0 - yend.fract()) * xgap);
            self.put_pixel(ypxl1 + 1, xpxl1, color, yend.fract() * xgap);
        } else {
            self.put_pixel(xpxl1, ypxl1, color, (1.0 - yend.fract()) * xgap);
            self.put_pixel(xpxl1, ypxl1 + 1, color, yend.fract() * xgap);
        }
        let mut intery = yend + gradient;

        // Handle second endpoint
        let xend = x1.round();
        let yend = y1 + gradient * (xend - x1);
        let xgap = (x1 + 0.5).fract();
        let xpxl2 = xend as i32;
        let ypxl2 = yend.floor() as i32;

        if steep {
            self.put_pixel(ypxl2, xpxl2, color, (1.0 - yend.fract()) * xgap);
            self.put_pixel(ypxl2 + 1, xpxl2, color, yend.fract() * xgap);
        } else {
            self.put_pixel(xpxl2, ypxl2, color, (1.0 - yend.fract()) * xgap);
            self.put_pixel(xpxl2, ypxl2 + 1, color, yend.fract() * xgap);
        }

        // Main loop
        if steep {
            for x in (xpxl1 + 1)..xpxl2 {
                let y = intery.floor() as i32;
                self.put_pixel(y, x, color, 1.0 - intery.fract());
                self.put_pixel(y + 1, x, color, intery.fract());
                intery += gradient;
            }
        } else {
            for x in (xpxl1 + 1)..xpxl2 {
                let y = intery.floor() as i32;
                self.put_pixel(x, y, color, 1.0 - intery.fract());
                self.put_pixel(x, y + 1, color, intery.fract());
                intery += gradient;
            }
        }
    }
}

pub fn draw_aa_analog_clock<W: Write>(
    out: &mut W,
    width: usize,
    height: usize,
    now: chrono::DateTime<chrono::Local>,
    seconds: bool,
    continuous: bool,
) -> std::io::Result<()> {
    use crate::analog::angle_coords;
    use chrono::Timelike;

    let r = ((width as f64 / 2.0).min(height as f64)) - 1.0;
    let cxf = width as f64 / 2.0;
    let cyf = height as f64;
    let cx = width / 2;
    let cy = height / 2;

    let mut canvas = RgbaCanvas::new(width, 2 * height);

    let sec = if continuous {
        (now.nanosecond() as f64) / 1e9 + (now.second() as f64)
    } else {
        now.second() as f64
    };

    let (sx, sy) = crate::analog::rotate_from_12(crate::analog::calculate_angle(60.0, sec), 0.9 * r);
    let m = (now.minute() as f64) + sec / 60.0;
    let (mx, my) = crate::analog::rotate_from_12(crate::analog::calculate_angle(60.0, m), 0.80 * r);
    let (hx, hy) = crate::analog::rotate_from_12(
        crate::analog::calculate_angle(12.0, ((now.hour() % 12) as f64) + m / 60.0),
        0.47 * r,
    );

    let min_dot_color = [255, 255, 255, 100];
    let hour_dot_color = [255, 20, 20, 180];

    if seconds {
        for n in 0..60 {
            let color = if n % 5 == 0 { hour_dot_color } else { min_dot_color };
            let (nx1, ny1) = crate::analog::rotate_from_12(crate::analog::calculate_angle(60.0, n as f64), r - 1.5);
            let (nx2, ny2) = crate::analog::rotate_from_12(crate::analog::calculate_angle(60.0, n as f64), r + 0.5);
            canvas.draw_aa_line(
                cxf + (nx1 as f64),
                cyf + (ny1 as f64),
                cxf + (nx2 as f64),
                cyf + (ny2 as f64),
                color,
            );
        }
        canvas.draw_aa_line(cxf, cyf, cxf + (sx as f64), cyf + (sy as f64), [0x50, 0x80, 0x50, 255]);
    }

    canvas.draw_aa_line(cxf, cyf, cxf + (mx as f64), cyf + (my as f64), [0x2C, 0x59, 0xD4, 255]);
    canvas.draw_aa_line(cxf, cyf, cxf + (hx as f64), cyf + (hy as f64), [255, 167, 10, 255]);

    // Render 2 * height canvas to terminal using half-blocks
    for y in 0..height {
        for x in 0..width {
            let top = canvas.data[(2 * y) * width + x];
            let bot = canvas.data[(2 * y + 1) * width + x];

            if top[3] > 0 || bot[3] > 0 {
                out.queue(MoveTo(x as u16, y as u16))?;
                out.queue(SetForegroundColor(Color::Rgb {
                    r: bot[0],
                    g: bot[1],
                    b: bot[2],
                }))?;
                out.queue(SetBackgroundColor(Color::Rgb {
                    r: top[0],
                    g: top[1],
                    b: top[2],
                }))?;
                write!(out, "▄")?;
            }
        }
    }
    out.queue(ResetColor)?;

    if !seconds {
        for n in (5..=60).step_by(5) {
            let (mut nx, ny) = angle_coords(60.0, (n % 60) as f64, r);
            let m = n / 5;
            if m >= 10 {
                nx -= 1;
            }
            let px = (cx as i32 + nx).max(0) as u16;
            let py = (cy as i32 + (ny - 1) / 2).max(0) as u16;
            out.queue(MoveTo(px, py))?;
            write!(out, "{}", m)?;
        }
    }

    Ok(())
}
