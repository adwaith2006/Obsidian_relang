//! 7-segment big number display module for terminal output.

pub const HEIGHT: usize = 5;
pub const WIDTH: usize = 4;

/// ASCII 7-segment glyph definitions for digits 0-9, colon (::), and dot (..).
const RAW_NUMBERS: &str = r#"
 ━━ 
┃  ┃
    
┃  ┃
 ━━ 

    
   ┃
    
   ┃
    

 ━━ 
   ┃
 ━━ 
┃   
 ━━ 

 ━━ 
   ┃
 ━━ 
   ┃
 ━━ 

    
┃  ┃
 ━━ 
   ┃
    

 ━━ 
┃   
 ━━ 
   ┃
 ━━ 

 ━━ 
┃   
 ━━ 
┃  ┃
 ━━ 

 ━━ 
   ┃
    
   ┃
    

 ━━ 
┃  ┃
 ━━ 
┃  ┃
 ━━ 

 ━━ 
┃  ┃
 ━━ 
   ┃
 ━━ 

    
 :: 
    
    
    

    
 .. 
    
    
    
"#;

fn add_trailing_spaces(s: &str, extra: isize) -> String {
    let char_count = s.chars().count();
    let target_len = (WIDTH as isize + extra).max(0) as usize;
    if char_count < target_len {
        format!("{}{}", s, " ".repeat(target_len - char_count))
    } else {
        s.to_string()
    }
}

pub fn get_number_lines() -> Vec<String> {
    let lines: Vec<&str> = RAW_NUMBERS.split('\n').collect();
    let mut result = Vec::new();
    // Skip initial empty line
    let lines_slice = if !lines.is_empty() && lines[0].is_empty() {
        &lines[1..]
    } else {
        &lines[..]
    };

    for (i, &line) in lines_slice.iter().enumerate() {
        let extra = if i >= 10 * (HEIGHT + 1) { -1 } else { 1 };
        result.push(add_trailing_spaces(line, extra));
    }
    result
}

#[derive(Default)]
pub struct Display {
    pub lines: [String; HEIGHT],
}

impl Display {
    pub fn new() -> Self {
        Self {
            lines: std::array::from_fn(|_| String::new()),
        }
    }

    pub fn place_digit(&mut self, c: char, blink: bool, number_lines: &[String]) {
        let digit_idx = match c {
            '0'..='9' => (c as usize) - ('0' as usize),
            _ if blink => 11, // dot
            _ => 10,          // colon
        };

        let start = digit_idx * (HEIGHT + 1);
        for i in 0..HEIGHT {
            if start + i < number_lines.len() {
                self.lines[i].push_str(&number_lines[start + i]);
            }
        }
    }

    pub fn to_string_output(&self) -> String {
        self.lines.join("\n")
    }
}

pub fn time_string(num_str: &str, blink: bool) -> String {
    let number_lines = get_number_lines();
    let mut d = Display::new();
    for c in num_str.chars() {
        d.place_digit(c, blink, &number_lines);
    }
    d.to_string_output()
}
