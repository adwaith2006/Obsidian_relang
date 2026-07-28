#!/usr/bin/env python3
"""
Asciiquarium - An aquarium animation in ASCII art.
Ported from Perl to Python 3 using the standard library curses module.
"""

import curses
import random
import time
import sys
import argparse
import signal

# -----------------------------------------------------------------------------
# Color Definitions & Utilities
# -----------------------------------------------------------------------------

# Palette mapping for color mask characters:
# c/C: Cyan, r/R: Red, y/Y: Yellow, b/B: Blue, g/G: Green, m/M: Magenta, w/W: White, k/K: Black/Dark Gray
COLOR_PALETTE = ['c', 'C', 'r', 'R', 'y', 'Y', 'b', 'B', 'g', 'G', 'm', 'M']

def rand_color(color_mask: str) -> str:
    """Replaces digits 1-9 in color_mask with random color codes from COLOR_PALETTE."""
    chars = list(color_mask)
    for i in range(len(chars)):
        if chars[i].isdigit():
            chars[i] = random.choice(COLOR_PALETTE)
    return "".join(chars)

def prepare_mask(mask_str: str) -> str:
    """Prepares color mask by replacing '4' with 'W' (white eye)."""
    mask_str = mask_str.replace('4', 'W')
    return rand_color(mask_str)

def clean_art(art_str: str) -> str:
    """Replaces '?' placeholders in ASCII art with spaces."""
    return art_str.replace('?', ' ')

# -----------------------------------------------------------------------------
# Entity & Animation Engine
# -----------------------------------------------------------------------------

class Entity:
    def __init__(self, name="", type_name="", shape=None, color_mask=None,
                 position=None, speed=None, default_color='w',
                 auto_trans=True, physical=False, die_offscreen=False,
                 die_time=None, die_frame=None, death_cb=None, coll_handler=None,
                 frame_speed=1.0, depth=0):
        self.name = name
        self.type_name = type_name
        
        # Shapes can be a single multi-line string or a list of multi-line strings (frames)
        if isinstance(shape, str):
            self.shapes = [clean_art(shape)]
        elif isinstance(shape, list):
            self.shapes = [clean_art(s) for s in shape]
        else:
            self.shapes = [""]

        # Color masks match shapes
        if isinstance(color_mask, str):
            self.color_masks = [color_mask]
        elif isinstance(color_mask, list):
            self.color_masks = color_mask
        else:
            self.color_masks = None

        self.x = float(position[0]) if position else 0.0
        self.y = float(position[1]) if position else 0.0
        self.z = int(position[2]) if position and len(position) > 2 else depth

        self.dx = float(speed[0]) if speed else 0.0
        self.dy = float(speed[1]) if speed else 0.0
        self.dz = float(speed[2]) if speed and len(speed) > 2 else 0.0
        
        if speed and len(speed) > 3:
            self.frame_speed = float(speed[3])
        else:
            self.frame_speed = frame_speed

        self.default_color = default_color
        self.auto_trans = auto_trans
        self.physical = physical
        self.die_offscreen = die_offscreen
        self.die_time = die_time
        self.die_frame = die_frame
        self.death_cb = death_cb
        self.coll_handler = coll_handler

        self.current_frame = 0.0
        self.alive = True
        self.collisions = []
        self.ticks = 0

    @property
    def current_shape_str(self) -> str:
        idx = int(self.current_frame) % len(self.shapes)
        return self.shapes[idx]

    @property
    def current_mask_str(self) -> str:
        if not self.color_masks:
            return ""
        idx = int(self.current_frame) % len(self.color_masks)
        return self.color_masks[idx]

    def get_lines_and_mask(self):
        shape_lines = self.current_shape_str.strip('\n').split('\n')
        mask_lines = self.current_mask_str.strip('\n').split('\n') if self.color_masks else []
        return shape_lines, mask_lines

    @property
    def width(self) -> int:
        lines, _ = self.get_lines_and_mask()
        return max((len(line) for line in lines), default=0)

    @property
    def height(self) -> int:
        lines, _ = self.get_lines_and_mask()
        return len(lines)

    def is_offscreen(self, screen_width, screen_height) -> bool:
        w = self.width
        h = self.height
        if self.x + w <= 0 or self.x >= screen_width:
            return True
        if self.y + h <= 0 or self.y >= screen_height:
            return True
        return False

    def kill(self):
        self.alive = False


class AnimationManager:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.entities = []
        self.color_map = {}
        self.init_colors()
        self.update_dimensions()

    def update_dimensions(self):
        self.height, self.width = self.stdscr.getmaxyx()

    def init_colors(self):
        curses.start_color()
        try:
            curses.use_default_colors()
            bg = -1
        except Exception:
            bg = curses.COLOR_BLACK

        # Initialize color pairs
        curses.init_pair(1, curses.COLOR_CYAN, bg)
        curses.init_pair(2, curses.COLOR_RED, bg)
        curses.init_pair(3, curses.COLOR_YELLOW, bg)
        curses.init_pair(4, curses.COLOR_BLUE, bg)
        curses.init_pair(5, curses.COLOR_GREEN, bg)
        curses.init_pair(6, curses.COLOR_MAGENTA, bg)
        curses.init_pair(7, curses.COLOR_WHITE, bg)
        curses.init_pair(8, curses.COLOR_BLACK, bg)

        self.color_map = {
            'c': curses.color_pair(1),
            'C': curses.color_pair(1) | curses.A_BOLD,
            'r': curses.color_pair(2),
            'R': curses.color_pair(2) | curses.A_BOLD,
            'y': curses.color_pair(3),
            'Y': curses.color_pair(3) | curses.A_BOLD,
            'b': curses.color_pair(4),
            'B': curses.color_pair(4) | curses.A_BOLD,
            'g': curses.color_pair(5),
            'G': curses.color_pair(5) | curses.A_BOLD,
            'm': curses.color_pair(6),
            'M': curses.color_pair(6) | curses.A_BOLD,
            'w': curses.color_pair(7),
            'W': curses.color_pair(7) | curses.A_BOLD,
            'k': curses.color_pair(8),
            'K': curses.color_pair(8) | curses.A_BOLD,
        }

    def get_attr(self, char_code: str, default_code='w'):
        if char_code in self.color_map:
            return self.color_map[char_code]
        return self.color_map.get(default_code, curses.color_pair(7))

    def add_entity(self, entity: Entity):
        self.entities.append(entity)

    def remove_all_entities(self):
        self.entities.clear()

    def get_entities_of_type(self, type_name: str):
        return [e for e in self.entities if e.type_name == type_name and e.alive]

    def update(self):
        self.update_dimensions()
        now = time.time()
        dead_entities = []

        for entity in list(self.entities):
            if not entity.alive:
                continue

            entity.ticks += 1
            entity.x += entity.dx
            entity.y += entity.dy
            entity.z += int(entity.dz)
            entity.current_frame += entity.frame_speed

            # Check expiration frame / time
            if entity.die_frame and entity.ticks >= entity.die_frame:
                entity.kill()
            elif entity.die_time and now >= entity.die_time:
                entity.kill()
            elif entity.die_offscreen and entity.is_offscreen(self.width, self.height):
                entity.kill()

            if not entity.alive:
                dead_entities.append(entity)

        # Collision detection among physical entities
        physical_entities = [e for e in self.entities if e.alive and e.physical]
        for i, e1 in enumerate(physical_entities):
            for e2 in physical_entities[i+1:]:
                if self.check_collision(e1, e2):
                    e1.collisions.append(e2)
                    e2.collisions.append(e1)

        # Run collision handlers & death callbacks
        for entity in list(self.entities):
            if entity.alive and entity.coll_handler:
                entity.coll_handler(entity, self)

        # Remove dead entities and invoke death callbacks
        for entity in dead_entities:
            if entity in self.entities:
                self.entities.remove(entity)
            if entity.death_cb:
                entity.death_cb(entity, self)

    def check_collision(self, e1: Entity, e2: Entity) -> bool:
        # AABB bounding box collision
        return not (e1.x + e1.width <= e2.x or
                    e2.x + e2.width <= e1.x or
                    e1.y + e1.height <= e2.y or
                    e2.y + e2.height <= e1.y)

    def redraw_screen(self):
        self.stdscr.erase()
        
        # Sort entities by Z depth descending so higher Z (background) is drawn first
        sorted_entities = sorted([e for e in self.entities if e.alive],
                                 key=lambda e: e.z, reverse=True)

        for entity in sorted_entities:
            shape_lines, mask_lines = entity.get_lines_and_mask()
            start_x = int(round(entity.x))
            start_y = int(round(entity.y))

            for r, line in enumerate(shape_lines):
                screen_y = start_y + r
                if screen_y < 0 or screen_y >= self.height - 1:
                    continue

                mask_line = mask_lines[r] if r < len(mask_lines) else ""

                for c, ch in enumerate(line):
                    screen_x = start_x + c
                    if screen_x < 0 or screen_x >= self.width - 1:
                        continue

                    # Transparent spaces
                    if entity.auto_trans and ch == ' ':
                        continue

                    color_code = mask_line[c] if c < len(mask_line) else entity.default_color
                    attr = self.get_attr(color_code, entity.default_color)

                    try:
                        self.stdscr.addch(screen_y, screen_x, ch, attr)
                    except curses.error:
                        pass

        self.stdscr.refresh()


# -----------------------------------------------------------------------------
# Asciiquarium ASCII Art & Setup
# -----------------------------------------------------------------------------

DEPTHS = {
    'guiText': 0,
    'gui': 1,
    'shark': 2,
    'fish_start': 3,
    'fish_end': 20,
    'seaweed': 21,
    'castle': 22,
    'water_line3': 2,
    'water_gap3': 3,
    'water_line2': 4,
    'water_gap2': 5,
    'water_line1': 6,
    'water_gap1': 7,
    'water_line0': 8,
    'water_gap0': 9,
}

# -----------------------------------------------------------------------------
# Environment & Castle
# -----------------------------------------------------------------------------

def add_environment(anim: AnimationManager):
    water_segments = [
        "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~",
        "^^^^ ^^^  ^^^   ^^^    ^^^^      ",
        "^^^^      ^^^^     ^^^    ^^     ",
        "^^      ^^^^      ^^^    ^^^^^^  "
    ]
    segment_size = len(water_segments[0])
    repeat_count = int(anim.width / segment_size) + 1

    for i, seg in enumerate(water_segments):
        tiled_seg = seg * repeat_count
        anim.add_entity(Entity(
            name=f"water_seg_{i}",
            type_name="waterline",
            shape=tiled_seg,
            position=[0, i + 5, DEPTHS[f'water_line{i}']],
            default_color='c',
            depth=22,
            physical=True
        ))

def add_castle(anim: AnimationManager):
    castle_image = """
               T~~
               |
              /^\\
             /   \\
 _   _   _  /     \\  _   _   _
[ ]_[ ]_[ ]/ _   _ \\[ ]_[ ]_[ ]
|_=__-_ =_|_[ ]_[ ]_|_=-___-__|
 | _- =  | =_ = _    |= _=   |
 |= -[]  |- = _ =    |_-=_[] |
 | =_    |= - ___    | =_ =  |
 |=  []- |-  /| |\\   |=_ =[] |
 |- =_   | =| | | |  |- = -  |
 |_______|__|_|_|_|__|_______|
"""
    castle_mask = """
                RR

              yyy
             y   y
            y     y
           y       y



              yyy
             yy yy
            y y y y
            yyyyyyy
"""
    anim.add_entity(Entity(
        name="castle",
        shape=castle_image,
        color_mask=castle_mask,
        position=[anim.width - 32, anim.height - 13, DEPTHS['castle']],
        default_color='K'
    ))

# -----------------------------------------------------------------------------
# Seaweed
# -----------------------------------------------------------------------------

def add_all_seaweed(anim: AnimationManager):
    count = int(anim.width / 15)
    for _ in range(count):
        add_seaweed(None, anim)

def add_seaweed(old_seaweed, anim: AnimationManager):
    height = random.randint(3, 6)
    frame0, frame1 = "", ""
    for i in range(1, height + 1):
        if i % 2 == 1:
            frame0 += "(\n"
            frame1 += " )\n"
        else:
            frame0 += " )\n"
            frame1 += "(\n"

    x = random.randint(1, max(1, anim.width - 2))
    y = anim.height - height
    anim_speed = random.uniform(0.0, 0.05) + 0.25
    die_time = time.time() + random.randint(4 * 60, 12 * 60)

    anim.add_entity(Entity(
        name=f"seaweed_{random.random()}",
        shape=[frame0, frame1],
        position=[x, y, DEPTHS['seaweed']],
        speed=[0, 0, 0, anim_speed],
        die_time=die_time,
        death_cb=add_seaweed,
        default_color='g'
    ))

# -----------------------------------------------------------------------------
# Bubbles
# -----------------------------------------------------------------------------

def add_bubble(fish: Entity, anim: AnimationManager):
    bx = fish.x
    if fish.dx > 0:
        bx += fish.width
    by = fish.y + int(fish.height / 2)
    bz = fish.z - 1

    anim.add_entity(Entity(
        shape=['.', 'o', 'O', 'O', 'O'],
        type_name='bubble',
        position=[bx, by, bz],
        speed=[0, -1, 0, 0.1],
        die_offscreen=True,
        physical=True,
        coll_handler=bubble_collision,
        default_color='C'
    ))

def bubble_collision(bubble: Entity, anim: AnimationManager):
    for col in bubble.collisions:
        if col.type_name == 'waterline' or bubble.y <= 8:
            bubble.kill()
            break

# -----------------------------------------------------------------------------
# Fish Definitions & Creation
# -----------------------------------------------------------------------------

NEW_FISH_IMAGES = [
    # Fish 0
    ("""
   \\
  / \\
>=_('>
  \\_/
   /
""",
"""
   1
  1 1
663745
  111
   3
""",
"""
  /
 / \\
<')_=<
 \\_/
  \\
""",
"""
  2
 111
547366
 111
  3
"""),
    # Fish 1
    ("""
     ,
     }\\
\\  .'  `\\
}}<   ( 6>
/  `,  .'
     }/
     '
""",
"""
     2
     22
6  11  11
661   7 45
6  11  11
     33
     3
""",
"""
    ,
   /{
 /'  `.  /
<6 )   >{{
 `.  ,'  \\
   \\{
    `
""",
"""
    2
   22
 11  11  6
54 7   166
 11  11  6
   33
    3
"""),
    # Fish 2
    ("""
            \\'`.
             )  \\
(`.??????_.-`' ' '`-.
 \\ `.??.`        (o) \\_
  >  ><     (((       (
 / .`??`._      /_|  /'
(.`???????`-. _  _.-`
            /__/'
""",
"""
            1111
             1  1
111      11111 1 1111
 1 11  11        141 11
  1  11     777       5
 1 11  111      333  11
111       111 1  1111
            11111
""",
"""
       .'`/
      /  (
  .-'` ` `'-._??????.')
_/ (o)        '.??.' /
)       )))     ><  <
`\\  |_\\      _.'??'. \\
  '-._  _ .-'???????'.)
      `\\__\\
""",
"""
       1111
      1  1
  1111 1 11111      111
11 141        11  11 1
5       777     11  1
11  333      111  11 1
  1111  1 111       111
      11111
"""),
    # Fish 3
    ("""
       ,--,_
__    _\\.---'-.
\\ '.-"     // o\\
/_.'-._    \\\\  /
       `"--(/"`
""",
"""
       22222
66    121111211
6 6111     77 41
6661111    77  1
       11113311
""",
"""
    _,--,
 .-'---./_    __
/o \\\\     "-.' /
\\  //    _.-'._\\
 `"\\)--"`
""",
"""
    22222
 112111121    66
14 77     1116 6
1  77    1111666
 11331111
""")
]

OLD_FISH_IMAGES = [
    # Fish 0
    ("""
       \\
     ...\\..,
\\  /'       \\
 >=     (  ' >
/  \\      / /
    `"'"'/''
""",
"""
       2
     1112111
6  11       1
 66     7  4 5
6  1      3 1
    11111311
""",
"""
      /
  ,../...
 /       '\\  /
< '  )     =<
 \\ \\      /  \\
  `'\\' '"'"'
""",
"""
      2
  1112111
 1       11  6
5 4  7     66
 1 3      1  6
  11311111
"""),
    # Fish 1
    ("""
    \\
\\ /--\\
>=  (o>
/ \\__/
    /
""",
"""
    2
6 1111
66  745
6 1111
    3
""",
"""
  /
 /--\\ /
<o)  =<
 \\__/ \\
  \\
""",
"""
  2
 1111 6
547  66
 1111 6
  3
"""),
    # Fish 2
    ("""
       \\:.
\\;,   ,;\\\\\\\\,,
  \\\\\\\\;;:::::::o
  ///;;::::::::<
 /;` ``/////``
""",
"""
       222
666   1122211
  6661111111114
  66611111111115
 666 113333311
""",
"""
      .:/
   ,,///;,   ,;/
 o:::::::;;///
>::::::::;;\\\\\\\\\\
  ''\\\\\\\\\\\\\\\\\\'' ';\\
""",
"""
      222
   1122211   666
 4111111111666
51111111111666
  113333311 666
"""),
    # Fish 3
    ("""
  __
><_'>
   '
""",
"""
  11
61145
   3
""",
"""
 __
<'_><
 `
""",
"""
 11
54116
 3
"""),
    # Fish 4
    ("""
   ..\\,
>='   ('>
  '''/''
""",
"""
   1121
661   745
  111311
""",
"""
  ,/..
<')   `=<
 ``\\```
""",
"""
  1211
547   166
 113111
"""),
    # Fish 5
    ("""
   \\
  / \\
>=_('>
  \\_/
   /
""",
"""
   2
  1 1
661745
  111
   3
""",
"""
  /
 / \\
<')_=<
 \\_/
  \\
""",
"""
  2
 1 1
547166
 111
  3
"""),
    # Fish 6
    ("""
  ,\\
>=('>
  '/
""",
"""
  12
66745
  13
""",
"""
 /,
<')=<
 \\`
""",
"""
 21
54766
 31
"""),
    # Fish 7
    ("""
  __
\\/ o\\
/\\__/
""",
"""
  11
61 41
61111
""",
"""
 __
/o \\/
\\__/\\
""",
"""
 11
14 16
11116
""")
]

def add_all_fish(anim: AnimationManager, use_new_fish: bool):
    screen_size = max(1, (anim.height - 9) * anim.width)
    count = int(screen_size / 350)
    for _ in range(count):
        add_fish(None, anim, use_new_fish)

def add_fish(old_fish, anim: AnimationManager, use_new_fish: bool):
    if use_new_fish and random.randint(0, 11) > 8:
        fish_set = NEW_FISH_IMAGES
    else:
        fish_set = OLD_FISH_IMAGES

    fish_tuple = random.choice(fish_set)
    is_left = random.choice([True, False])

    if is_left:
        shape_str, mask_str = fish_tuple[2], fish_tuple[3]
        speed = -(random.uniform(0, 2) + 0.25)
    else:
        shape_str, mask_str = fish_tuple[0], fish_tuple[1]
        speed = random.uniform(0, 2) + 0.25

    color_mask = prepare_mask(mask_str)
    depth = random.randint(DEPTHS['fish_start'], DEPTHS['fish_end'])

    fish_ent = Entity(
        type_name='fish',
        shape=shape_str,
        color_mask=color_mask,
        position=[0, 0, depth],
        speed=[speed, 0, 0],
        die_offscreen=True,
        death_cb=lambda f, a: add_fish(f, a, use_new_fish),
        physical=True,
        coll_handler=fish_collision
    )

    max_h = 9
    min_h = max(max_h, anim.height - fish_ent.height)
    fish_ent.y = float(random.randint(max_h, min_h))

    if is_left:
        fish_ent.x = float(anim.width - 2)
    else:
        fish_ent.x = float(1 - fish_ent.width)

    # Attach fish callback
    def cb(f: Entity, a: AnimationManager):
        if random.randint(0, 99) > 97:
            add_bubble(f, a)

    fish_ent.coll_handler = lambda f, a: (cb(f, a), fish_collision(f, a))
    anim.add_entity(fish_ent)

def fish_collision(fish: Entity, anim: AnimationManager):
    for col in fish.collisions:
        if col.type_name == 'teeth' and fish.height <= 5:
            add_splat(anim, col.x, col.y, col.z)
            fish.kill()
            break

def add_splat(anim: AnimationManager, x: float, y: float, z: int):
    splat_frames = [
        "\n   .\n  ***\n   '\n",
        "\n  \",*;`\n  \"*,**\n  *\"'~'\n",
        "  , ,\n \" \",\"'\n *\" *'\"\n  \" ; .\n",
        "* ' , ' `\n' ` * . '\n ' `' \",'\n* ' \" * .\n\" * ', '\n"
    ]

    anim.add_entity(Entity(
        shape=splat_frames,
        position=[x - 4, y - 2, z - 2],
        default_color='R',
        frame_speed=0.25,
        die_frame=15
    ))

# -----------------------------------------------------------------------------
# Special Surface & Creature Objects
# -----------------------------------------------------------------------------

def random_object(dead_obj, anim: AnimationManager, use_new_fish=True, use_new_monster=True):
    choices = [add_ship, add_whale, add_shark]
    choices.append(lambda o, a: add_big_fish(o, a, use_new_fish))
    choices.append(lambda o, a: add_monster(o, a, use_new_monster))

    obj_func = random.choice(choices)
    obj_func(dead_obj, anim)

def add_ship(old_ent, anim: AnimationManager):
    ship_shapes = [
        """
     |    |    |
    )_)  )_)  )_)
   )___))___))___)\\
  )____)____)_____)\\\\
_____|____|____|____\\\\\\__
\\                   /
""",
        """
         |    |    |
        (_(  (_(  (_(
      /(___((___((___(
    //(_____(____(____(
__///____|____|____|_____
    \\                   /
"""
    ]
    ship_masks = [
        """
     y    y    y

                  w
                   ww
yyyyyyyyyyyyyyyyyyyywwwyy
y                   y
""",
        """
         y    y    y

      w
    ww
yywwwyyyyyyyyyyyyyyyyyyyy
    y                   y
"""
    ]

    is_left = random.choice([True, False])
    if is_left:
        idx = 1
        speed = -1.0
        x = anim.width - 2
    else:
        idx = 0
        speed = 1.0
        x = -24

    anim.add_entity(Entity(
        shape=ship_shapes[idx],
        color_mask=ship_masks[idx],
        position=[x, 0, DEPTHS['water_gap1']],
        speed=[speed, 0, 0],
        default_color='W',
        die_offscreen=True,
        death_cb=lambda o, a: random_object(o, a)
    ))

def add_whale(old_ent, anim: AnimationManager):
    whale_images = [
        """
        .-----:
      .'       `.
,    /       (o) \\
\\`._/          ,__)
""",
        """
    :-----.
  .'       `.
 / (o)       \\    ,
(__,          \\_.'/
"""
    ]
    whale_masks = [
        """
             C C
           CCCCCCC
           C  C  C
        BBBBBBB
      BB       BB
B    B       BWB B
BBBBB          BBBB
""",
        """
   C C
 CCCCCCC
 C  C  C
    BBBBBBB
  BB       BB
 B BWB       B    B
BBBB          BBBBB
"""
    ]
    water_spout = [
        "\n\n   :\n",
        "\n   :\n   :\n",
        "  . .\n  -:-\n   :\n",
        "  . .\n .-:-\n   :\n",
        "  . .\n'.-:-.`\n'  :  '\n",
        "\n .- -.\n;  :  ;\n",
        "\n\n;     ;\n"
    ]

    is_left = random.choice([True, False])
    if is_left:
        idx = 1
        speed = -1.0
        x = anim.width - 2
        spout_align = 1
    else:
        idx = 0
        speed = 1.0
        x = -18
        spout_align = 11

    whale_anim = []
    whale_anim_mask = []

    # 5 frames no spout
    for _ in range(5):
        whale_anim.append("\n\n\n" + whale_images[idx])
        whale_anim_mask.append(whale_masks[idx])

    # 7 spout frames
    for spout_frame in water_spout:
        aligned_lines = [(" " * spout_align) + line for line in spout_frame.split("\n")]
        aligned_spout = "\n".join(aligned_lines) + "\n"
        whale_anim.append(aligned_spout + whale_images[idx])
        whale_anim_mask.append(whale_masks[idx])

    anim.add_entity(Entity(
        shape=whale_anim,
        color_mask=whale_anim_mask,
        position=[x, 0, DEPTHS['water_gap2']],
        speed=[speed, 0, 0, 1.0],
        default_color='W',
        die_offscreen=True,
        death_cb=lambda o, a: random_object(o, a)
    ))

def add_monster(old_ent, anim: AnimationManager, use_new_monster=True):
    if use_new_monster:
        add_new_monster(old_ent, anim)
    else:
        add_old_monster(old_ent, anim)

def add_new_monster(old_ent, anim: AnimationManager):
    monster_images = [
        [
            r"""
         _   _                     _   _       _a_a
       _{.`=`.}_       _   _      _{.`=`.}_    {/ ''\_
 _    {.'  _  '.}    {.`'`.}    {.'  _  '.}  {|  ._oo)
{ \   {/  .' '.  \}  {/ .-. \}  {/  .' '.  \} {/  |
""",
            r"""
                      _   _                    _a_a
  _      _   _      _{.`=`.}_       _   _      {/ ''\_
 { \    {.`'`.}    {.'  _  '.}    {.`'`.}    {|  ._oo)
  \ \   {/ .-. \}  {/  .' '.  \}  {/ .-. \}   {/  |
"""
        ],
        [
            r"""
   a_a_       _   _                     _   _
 _/'' \}    _{.`=`.}_       _   _      _{.`=`.}_
(oo_.  |}  {.'  _  '.}    {.`'`.}    {.'  _  '.}    _
    |  \}  {/  .' '.  \}  {/ .-. \}  {/  .' '.  \}  / }
""",
            r"""
   a_a_                    _   _
 _/'' \}      _   _      _{.`=`.}_       _   _      _
(oo_.  |}    {.`'`.}    {.'  _  '.}    {.`'`.}    / }
    |  \}   {/ .-. \}  {/  .' '.  \}  {/ .-. \}  / /
"""
        ]
    ]
    monster_masks = [
        "                                                W W\n\n\n",
        "   W W\n\n\n"
    ]

    is_left = random.choice([True, False])
    if is_left:
        idx = 1
        speed = -2.0
        x = anim.width - 2
    else:
        idx = 0
        speed = 2.0
        x = -54

    mask_list = [monster_masks[idx], monster_masks[idx]]

    anim.add_entity(Entity(
        shape=monster_images[idx],
        color_mask=mask_list,
        position=[x, 2, DEPTHS['water_gap2']],
        speed=[speed, 0, 0, 0.25],
        default_color='g',
        die_offscreen=True,
        death_cb=lambda o, a: random_object(o, a)
    ))

def add_old_monster(old_ent, anim: AnimationManager):
    monster_images = [
        [
            "\n                                                          ____\n            __                                           /   o  \\\n          /    \\        _                     _         /     ____ >\n  _      |  __  |     /   \\        _        /   \\      |     |\n | \\     |  ||  |    |     |     /   \\     |     |     |     |\n",
            "\n                                                          ____\n                                             __          /   o  \\\n             _                     _        /    \\      /     ____ >\n    _      /   \\        _        /   \\     |  __  |    |     |\n   | \\    |     |     /   \\     |     |    |  ||  |    |     |\n",
            "\n                                                          ____\n                                  __                     /   o  \\\n _                      _        /    \\        _        /     ____ >\n| \\          _        /   \\     |  __  |     /   \\     |     |\n \\ \\       /   \\     |     |    |  ||  |    |     |    |     |\n",
            "\n                                                          ____\n                       __                                /   o  \\\n  _          _        /    \\        _                   /     ____ >\n | \\       /   \\     |  __  |     /   \\        _       |     |\n  \\ \\     |     |    |  ||  |    |     |     /   \\     |     |\n"
        ],
        [
            "\n    ____\n  /  o   \\                                          __\n< ____     \\       _                     _        /    \\\n      |     |    /   \\        _        /   \\     |  __  |      _\n      |     |   |     |     /   \\     |     |    |  ||  |     / |\n",
            "\n    ____\n  /  o   \\         __\n< ____     \\     /    \\       _                     _\n      |     |   |  __  |    /   \\        _        /   \\       _\n      |     |   |  ||  |   |     |     /   \\     |     |     / |\n",
            "\n    ____\n  /  o   \\                    __\n< ____     \\       _        /    \\       _                      _\n      |     |    /   \\     |  __  |    /   \\        _          / |\n      |     |   |     |    |  ||  |   |     |     /   \\       / /\n",
            "\n    ____\n  /  o   \\                               __\n< ____     \\                  _        /    \\       _          _\n      |     |      _        /   \\     |  __  |    /   \\       / |\n      |     |    /   \\     |     |    |  ||  |   |     |     / /\n"
        ]
    ]
    monster_masks = [
        "\n\n                                                            W\n\n\n",
        "\n\n     W\n\n\n"
    ]

    is_left = random.choice([True, False])
    if is_left:
        idx = 1
        speed = -2.0
        x = anim.width - 2
    else:
        idx = 0
        speed = 2.0
        x = -64

    mask_list = [monster_masks[idx]] * 4

    anim.add_entity(Entity(
        shape=monster_images[idx],
        color_mask=mask_list,
        position=[x, 2, DEPTHS['water_gap2']],
        speed=[speed, 0, 0, 0.25],
        default_color='g',
        die_offscreen=True,
        death_cb=lambda o, a: random_object(o, a)
    ))

def add_big_fish(old_ent, anim: AnimationManager, use_new_fish=True):
    if use_new_fish and random.randint(0, 2) > 1:
        add_big_fish_2(old_ent, anim)
    else:
        add_big_fish_1(old_ent, anim)

def add_big_fish_1(old_ent, anim: AnimationManager):
    bf_images = [
        """
 ______
`""-.  `````-----.....__
     `.  .      .       `-.
       :     .     .       `.
  ,     :   .    .          _ :
: `.   :                  (@) `._
 `. `..'     .     =`-.       .__)
   ;     .        =  ~  :     .-"
 .' .'`.   .    .  =.-'  `._ .'
: .'   :               .   .'
 '   .'  .    .     .   .-'
   .'____....----''.'=.'
   ""             .'.'
               ''"'`
""",
        """
                           ______
          __.....-----'''''  .-""'
       .-'       .      .  .'
     .'       .     .     :
    : _          .    .   :     ,
 _.' (@)                  :   .' :
(__.       .-'=     .     `..' .'
 "-.     :  ~  =        .     ;
   `. _.'  `-.=  .    .   .'`. `.
     `.   .               :   `. :
       `-.   .     .    .  `.   `
          `.=`.``----....____`.
            `.`.             ""
              '`"``
"""
    ]
    bf_masks = [
        """
 111111
11111  11111111111111111
     11  2      2       111
       1     2     2       11
 1     1   2    2          1 1
1 11   1                  1W1 111
 11 1111     2     1111       1111
   1     2        1  1  1     111
 11 1111   2    2  1111  111 11
1 11   1               2   11
 1   11  2    2     2   111
   111111111111111111111
   11             1111
               11111
""",
        """
                           111111
          11111111111111111  11111
       111       2      2  11
     11       2     2     1
    1 1          2    2   1     1
 111 1W1                  1   11 1
1111       1111     2     1111 11
 111     1  1  1        2     1
   11 111  1111  2    2   1111 11
     11   2               1   11 1
       111   2     2    2  11   1
          111111111111111111111
            1111             11
              11111
"""
    ]

    is_left = random.choice([True, False])
    if is_left:
        idx = 1
        speed = -3.0
        x = anim.width - 1
    else:
        idx = 0
        speed = 3.0
        x = -34

    max_h = 9
    min_h = max(max_h, anim.height - 15)
    y = random.randint(max_h, min_h)

    color_mask = rand_color(bf_masks[idx])

    anim.add_entity(Entity(
        shape=bf_images[idx],
        color_mask=color_mask,
        position=[x, y, DEPTHS['shark']],
        speed=[speed, 0, 0],
        default_color='Y',
        die_offscreen=True,
        death_cb=lambda o, a: random_object(o, a)
    ))

def add_big_fish_2(old_ent, anim: AnimationManager):
    bf_images = [
        r"""
                _ _ _
             .='\\ \\ \\`"=,
           .'\\ \\ \\ \\ \\ \\ \\
\\'=._     / \\ \\ \\_\\_\\_\\_\\_\\
\\'=._'.  /\\ \\,-"`- _ - _ - '-.
  \\`=._\\|'.\\/- _ - _ - _ - _- \\
  ;"= ._\\=./_ -_ -_ \{`"=_    @ \\
   ;="_-_=- _ -  _ - \{"=_"-     \\
   ;_=_--_.,          \{_.='   .-/
  ;.="` / ';\\        _.     _.-`
  /_.='/ \\/ /;._ _ _\{.-;`/"`
/._=_.'   '/ / / / /\{.= /
/.='      `'./_/_.=`\{_/
""",
        r"""
            _ _ _
        ,="`/ / /'=.
       / / / / / / /'.
      /_/_/_/_/_/ / / \\     _.='/
   .-' - _ - _ -`"-,/ /\\  .'_.='/
  / -_ - _ - _ - _ -\\/.'|/_.=`/
 / @    _="`\} _- _- _\\.=/_. =";
/     -"_="\} - _  - _ -=_-_"=;
\\-.   '=._\}          ,._--_=_;
 `-._     ._        /;' \\ `"=.;
     `"\\`;-.\}_ _ _.;\\ \\/ \\'=._\\
        \\ =.\}\\ \\ \\ \\ \\'   '._=_.\\
         \\_\}`=._\\_\\.'`       '=.\\
"""
    ]
    bf_masks = [
        """
                1 1 1
             1111 1 11111
           111 1 1 1 1 1 1
11111     1 1 1 11111111111
1111111  11 111112 2 2 2 2 111
  111111111112 2 2 2 2 2 2 22 1
  111 1111 12 22 22 11111    W 1
   11111112 2 2  2 2 111111     1
   111111111          11111   111
  11111 11111        11     1111
  111111 11 1111 1 111111111
1111111   11 1 1 1 1111 1
1111       1111111111111
""",
        """
            1 1 1
        11111 1 1111
       1 1 1 1 1 1 111
      11111111111 1 1 1     11111
   111 2 2 2 2 211111 11  1111111
  1 22 2 2 2 2 2 2 211111111111
 1 W    11111 22 22 2111111 111
1     111111 2 2  2 2 21111111
111   11111          111111111
 1111     11        111 1 11111
     111111111 1 1111 11 111111
        1 1111 1 1 1 11   1111111
         1111111111111       1111
"""
    ]

    is_left = random.choice([True, False])
    if is_left:
        idx = 1
        speed = -2.5
        x = anim.width - 1
    else:
        idx = 0
        speed = 2.5
        x = -33

    max_h = 9
    min_h = max(max_h, anim.height - 14)
    y = random.randint(max_h, min_h)

    color_mask = rand_color(bf_masks[idx])

    anim.add_entity(Entity(
        shape=bf_images[idx],
        color_mask=color_mask,
        position=[x, y, DEPTHS['shark']],
        speed=[speed, 0, 0],
        default_color='Y',
        die_offscreen=True,
        death_cb=lambda o, a: random_object(o, a)
    ))

def add_shark(old_ent, anim: AnimationManager):
    shark_shapes = [
        """
                              __
                             ( `\\
  ,                          )   `\\
;' `.                        (     `\\__
 ;   `.             __..---''          `~~~~-._
  `.   `.____...--''                       (b  `--._
    >                     _.-'      .((      ._     )
  .`.-`--...__         .-'     -.___.....-(|/|/|/|/'
 ;.'         `. ...----`.___.',,,_______......---'
 '           '-'
""",
        """
                     __
                    /' )
                  /'   (                          ,
              __/'     )                        .' `;
      _.-~~~~'          ``---..__             .'   ;
 _.--'  b)                       ``--...____.'   .'
(     _.      )).      `-._                     <
 `\\|\\|\\|\\|)-.....___.-     `-.         __...--'-.'.
   `---......_______,,,`.___.'----... .'         `.;
                                     `-`           `
"""
    ]
    shark_masks = [
        "\n\n\n\n                                           cR\n\n                                          cWWWWWWWW\n\n",
        "\n\n\n\n        Rc\n\n  WWWWWWWWc\n\n"
    ]

    is_left = random.choice([True, False])
    max_h = 9
    min_h = max(max_h, anim.height - 19)
    y = random.randint(max_h, min_h)

    if is_left:
        idx = 1
        speed = -2.0
        x = anim.width - 2
        teeth_x = x + 9
    else:
        idx = 0
        speed = 2.0
        x = -53
        teeth_x = -9

    teeth_y = y + 7

    anim.add_entity(Entity(
        type_name='teeth',
        shape="*",
        position=[teeth_x, teeth_y, DEPTHS['shark'] + 1],
        depth=DEPTHS['fish_end'] - DEPTHS['fish_start'],
        speed=[speed, 0, 0],
        physical=True
    ))

    anim.add_entity(Entity(
        type_name="shark",
        shape=shark_shapes[idx],
        color_mask=shark_masks[idx],
        position=[x, y, DEPTHS['shark']],
        speed=[speed, 0, 0],
        default_color='C',
        die_offscreen=True,
        death_cb=shark_death
    ))

def shark_death(shark: Entity, anim: AnimationManager):
    teeth_objs = anim.get_entities_of_type('teeth')
    for teeth in teeth_objs:
        teeth.kill()
    random_object(shark, anim)

# -----------------------------------------------------------------------------
# Main Application Loop & Controls
# -----------------------------------------------------------------------------

def setup_aquarium(anim: AnimationManager, use_new_fish: bool, use_new_monster: bool):
    anim.remove_all_entities()
    add_environment(anim)
    add_castle(anim)
    add_all_seaweed(anim)
    add_all_fish(anim, use_new_fish)
    random_object(None, anim, use_new_fish, use_new_monster)

def main(stdscr):
    parser = argparse.ArgumentParser(description="ASCII Aquarium in Python")
    parser.add_argument('-c', '--classic', action='store_true', help="Classic mode (no new fish or monsters)")
    args, _ = parser.parse_known_args()

    use_new_fish = not args.classic
    use_new_monster = not args.classic

    curses.curs_set(0)
    stdscr.nodelay(True)

    anim = AnimationManager(stdscr)
    setup_aquarium(anim, use_new_fish, use_new_monster)

    paused = False
    last_dimensions = (anim.height, anim.width)

    # Frame timing (~20 FPS -> 50ms tick time)
    tick_delay = 0.05

    while True:
        cycle_start = time.time()

        # Handle user input
        ch = stdscr.getch()
        if ch != -1:
            try:
                char_key = chr(ch).lower()
            except ValueError:
                char_key = ""

            if char_key == 'q':
                break
            elif char_key == 'r':
                setup_aquarium(anim, use_new_fish, use_new_monster)
            elif char_key == 'p':
                paused = not paused

        # Handle screen resize
        current_dimensions = stdscr.getmaxyx()
        if current_dimensions != last_dimensions:
            last_dimensions = current_dimensions
            setup_aquarium(anim, use_new_fish, use_new_monster)

        if not paused:
            anim.update()

        anim.redraw_screen()

        elapsed = time.time() - cycle_start
        sleep_time = max(0.001, tick_delay - elapsed)
        time.sleep(sleep_time)

if __name__ == '__main__':
    def signal_handler(sig, frame):
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        sys.exit(0)
