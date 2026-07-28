// sl.go — Steam Locomotive terminal animation
//
// Go port of the original C/Python sl implementation by Toyoda Masashi.
// All ASCII art is faithfully preserved from sl.h / sl.c.
//
// Usage:
//
//	go run sl.go [OPTIONS]
//	go build -o sl sl.go && ./sl
//
// Options: -a (accident), -F (fly), -c (C51), -l (logo), -d (dance)
package main

import (
	"fmt"
	"os"
	"os/exec"
	"os/signal"
	"strings"
	"syscall"
	"time"
)

// ---------------------------------------------------------------------------
// ASCII art — transcribed verbatim from sl.h
// ---------------------------------------------------------------------------

// D51 locomotive
const (
	d51Height   = 10
	d51Funnel   = 7
	d51Length   = 83
	d51Patterns = 6

	d51STR1 = "      ====        ________                ___________ "
	d51STR2 = "  _D _|  |_______/        \\__I_I_____===__|_________| "
	d51STR3 = "   |(_)---  |   H\\________/ |   |        =|___ ___|   "
	d51STR4 = "   /     |  |   H  |  |     |   |         ||_| |_||   "
	d51STR5 = "  |      |  |   H  |__--------------------| [___] |   "
	d51STR6 = "  | ________|___H__/__|_____/[][]~\\_______|       |   "
	d51STR7 = "  |/ |   |-----------I_____I [][] []  D   |=======|__ "

	d51WHL11 = "__/ =| o |=-~~\\  /~~\\  /~~\\  /~~\\ ____Y___________|__ "
	d51WHL12 = " |/-=|___|=    ||    ||    ||    |_____/~\\___/        "
	d51WHL13 = "  \\_/      \\O=====O=====O=====O_/      \\_/            "

	d51WHL21 = "__/ =| o |=-~~\\  /~~\\  /~~\\  /~~\\ ____Y___________|__ "
	d51WHL22 = " |/-=|___|=O=====O=====O=====O   |_____/~\\___/        "
	d51WHL23 = "  \\_/      \\__/  \\__/  \\__/  \\__/      \\_/            "

	d51WHL31 = "__/ =| o |=-O=====O=====O=====O \\ ____Y___________|__ "
	d51WHL32 = " |/-=|___|=    ||    ||    ||    |_____/~\\___/        "
	d51WHL33 = "  \\_/      \\__/  \\__/  \\__/  \\__/      \\_/            "

	d51WHL41 = "__/ =| o |=-~O=====O=====O=====O\\ ____Y___________|__ "
	d51WHL42 = " |/-=|___|=    ||    ||    ||    |_____/~\\___/        "
	d51WHL43 = "  \\_/      \\__/  \\__/  \\__/  \\__/      \\_/            "

	d51WHL51 = "__/ =| o |=-~~\\  /~~\\  /~~\\  /~~\\ ____Y___________|__ "
	d51WHL52 = " |/-=|___|=   O=====O=====O=====O|_____/~\\___/        "
	d51WHL53 = "  \\_/      \\__/  \\__/  \\__/  \\__/      \\_/            "

	d51WHL61 = "__/ =| o |=-~~\\  /~~\\  /~~\\  /~~\\ ____Y___________|__ "
	d51WHL62 = " |/-=|___|=    ||    ||    ||    |_____/~\\___/        "
	d51WHL63 = "  \\_/      \\_O=====O=====O=====O/      \\_/            "

	d51DEL = "                                                      "

	coal01  = "                              "
	coal02  = "                              "
	coal03  = "    _________________         "
	coal04  = "   _|                \\_____A  "
	coal05  = " =|                        |  "
	coal06  = " -|                        |  "
	coal07  = "__|________________________|_ "
	coal08  = "|__________________________|_ "
	coal09  = "   |_D__D__D_|  |_D__D__D_|   "
	coal10  = "    \\_/   \\_/    \\_/   \\_/    "
	coalDEL = "                              "
)

// LOGO / Small SL locomotive
const (
	logoHeight   = 6
	logoFunnel   = 4
	logoLength   = 84
	logoPatterns = 6

	logo1 = "     ++      +------ "
	logo2 = "     ||      |+-+ |  "
	logo3 = "   /---------|| | |  "
	logo4 = "  + ========  +-+ |  "

	lwhl11 = " _|--O========O~\\-+  "
	lwhl12 = "//// \\_/      \\_/    "
	lwhl21 = " _|--/O========O\\-+  "
	lwhl22 = "//// \\_/      \\_/    "
	lwhl31 = " _|--/~O========O-+  "
	lwhl32 = "//// \\_/      \\_/    "
	lwhl41 = " _|--/~\\------/~\\-+  "
	lwhl42 = "//// \\_O========O    "
	lwhl51 = " _|--/~\\------/~\\-+  "
	lwhl52 = "//// \\O========O/    "
	lwhl61 = " _|--/~\\------/~\\-+  "
	lwhl62 = "//// O========O_/    "

	lcoal1 = "____                 "
	lcoal2 = "|   \\@@@@@@@@@@@     "
	lcoal3 = "|    \\@@@@@@@@@@@@@_ "
	lcoal4 = "|                  | "
	lcoal5 = "|__________________| "
	lcoal6 = "   (O)       (O)     "

	lcar1 = "____________________ "
	lcar2 = "|  ___ ___ ___ ___ | "
	lcar3 = "|  |_| |_| |_| |_| | "
	lcar4 = "|__________________| "
	lcar5 = "|__________________| "
	lcar6 = "   (O)        (O)    "

	delLN = "                     "
)

// C51 locomotive
const (
	c51Height   = 11
	c51Funnel   = 7
	c51Length   = 87
	c51Patterns = 6

	c51DEL  = "                                                       "
	c51STR1 = "        ___                                            "
	c51STR2 = "       _|_|_  _     __       __             ___________"
	c51STR3 = "    D__/   \\_(_)___|  |__H__|  |_____I_Ii_()|_________| "
	c51STR4 = "     | `---'   |:: `--'  H  `--'         |  |___ ___|  "
	c51STR5 = "    +|~~~~~~~~++::~~~~~~~H~~+=====+~~~~~~|~~||_| |_||  "
	c51STR6 = "    ||        | ::       H  +=====+      |  |::  ...|  "
	c51STR7 = "|    | _______|_::-----------------[][]-----|       |  "

	c51WH11 = "| /~~ ||   |-----/~~~~\\  /[I_____I][][] --|||_______|__"
	c51WH12 = "------'|oOo|=[]=-      ||      ||      |  ||=======_|__"
	c51WH13 = "/~\\____|___|/~\\_|  O=======O=======O   |__|+-/~\\_|     "
	c51WH14 = "\\_/         \\_/  \\____/  \\____/  \\____/      \\_/       "

	c51WH21 = "| /~~ ||   |-----/~~~~\\  /[I_____I][][] --|||_______|__"
	c51WH22 = "------'|oOo|=[]=- O=======O=======O    |  ||=======_|__"
	c51WH23 = "/~\\____|___|/~\\_|      ||      ||      |__|+-/~\\_|     "
	c51WH24 = "\\_/         \\_/  \\____/  \\____/  \\____/      \\_/       "

	c51WH31 = "| /~~ ||   |-----/~~~~\\  /[I_____I][][] --|||_______|__"
	c51WH32 = "------'|oOo|==[]=- O=======O=======O   |  ||=======_|__"
	c51WH33 = "/~\\____|___|/~\\_|      ||      ||      |__|+-/~\\_|     "
	c51WH34 = "\\_/         \\_/  \\____/  \\____/  \\____/      \\_/       "

	c51WH41 = "| /~~ ||   |-----/~~~~\\  /[I_____I][][] --|||_______|__"
	c51WH42 = "------'|oOo|===[]=- O=======O=======O  |  ||=======_|__"
	c51WH43 = "/~\\____|___|/~\\_|      ||      ||      |__|+-/~\\_|     "
	c51WH44 = "\\_/         \\_/  \\____/  \\____/  \\____/      \\_/       "

	c51WH51 = "| /~~ ||   |-----/~~~~\\  /[I_____I][][] --|||_______|__"
	c51WH52 = "------'|oOo|===[]=-    ||      ||      |  ||=======_|__"
	c51WH53 = "/~\\____|___|/~\\_|    O=======O=======O |__|+-/~\\_|     "
	c51WH54 = "\\_/         \\_/  \\____/  \\____/  \\____/      \\_/       "

	c51WH61 = "| /~~ ||   |-----/~~~~\\  /[I_____I][][] --|||_______|__"
	c51WH62 = "------'|oOo|==[]=-     ||      ||      |  ||=======_|__"
	c51WH63 = "/~\\____|___|/~\\_|   O=======O=======O  |__|+-/~\\_|     "
	c51WH64 = "\\_/         \\_/  \\____/  \\____/  \\____/      \\_/       "
)

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

// Config holds the animation settings parsed from CLI arguments.
type Config struct {
	cols, lines int
	accident    bool
	logo        int // 0 = D51; >=1 = LOGO with (logo) extra cars
	fly         bool
	c51         bool
	dance       bool
}

// ---------------------------------------------------------------------------
// Smoke particle state
// ---------------------------------------------------------------------------

type smokeParticle struct {
	y, x        int
	ptrn, kind  int
}

var smokeParticles []smokeParticle

var smokeStr = [2][16]string{
	{"(   )", "(    )", "(    )", "(   )", "(  )", "(  )", "( )", "( )", "()", "()", "O", "O", "O", "O", "O", " "},
	{"(@@@)", "(@@@@)", "(@@@@)", "(@@@)", "(@@)", "(@@)", "(@)", "(@)", "@@", "@@", "@", "@", "@", "@", "@", " "},
}
var smokeEraser = [16]string{
	"     ", "      ", "      ", "     ", "    ", "    ", "   ", "   ", "  ", "  ",
	" ", " ", " ", " ", " ", " ",
}
var smokeDy = [16]int{2, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0}
var smokeDx = [16]int{-2, -1, 0, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 3, 3, 3}

// ---------------------------------------------------------------------------
// Canvas (rendering buffer)
// ---------------------------------------------------------------------------

// Canvas is a 2D character buffer representing one frame.
type Canvas struct {
	rows, cols int
	buf        [][]byte
}

func newCanvas(rows, cols int) *Canvas {
	buf := make([][]byte, rows)
	for i := range buf {
		buf[i] = []byte(strings.Repeat(" ", cols))
	}
	return &Canvas{rows: rows, cols: cols, buf: buf}
}

// addStr writes string s into the canvas at (y, x), clipping to bounds.
func (c *Canvas) addStr(y, x int, s string) {
	if y < 0 || y >= c.rows {
		return
	}
	for _, ch := range []byte(s) {
		if x >= c.cols {
			break
		}
		if x >= 0 {
			c.buf[y][x] = ch
		}
		x++
	}
}

// clear resets every cell to a space.
func (c *Canvas) clear() {
	for i := range c.buf {
		for j := range c.buf[i] {
			c.buf[i][j] = ' '
		}
	}
}

// flush renders the canvas to stdout: cursor home then all rows.
func (c *Canvas) flush() {
	var sb strings.Builder
	sb.WriteString("\x1b[H") // cursor home
	for row := 0; row < c.rows; row++ {
		sb.Write(c.buf[row])
		sb.WriteByte('\n')
	}
	fmt.Print(sb.String())
}

// ---------------------------------------------------------------------------
// Frame tables (indexed by wheel pattern)
// ---------------------------------------------------------------------------

var d51Frames = [d51Patterns][d51Height + 1]string{
	{d51STR1, d51STR2, d51STR3, d51STR4, d51STR5, d51STR6, d51STR7, d51WHL11, d51WHL12, d51WHL13, d51DEL},
	{d51STR1, d51STR2, d51STR3, d51STR4, d51STR5, d51STR6, d51STR7, d51WHL21, d51WHL22, d51WHL23, d51DEL},
	{d51STR1, d51STR2, d51STR3, d51STR4, d51STR5, d51STR6, d51STR7, d51WHL31, d51WHL32, d51WHL33, d51DEL},
	{d51STR1, d51STR2, d51STR3, d51STR4, d51STR5, d51STR6, d51STR7, d51WHL41, d51WHL42, d51WHL43, d51DEL},
	{d51STR1, d51STR2, d51STR3, d51STR4, d51STR5, d51STR6, d51STR7, d51WHL51, d51WHL52, d51WHL53, d51DEL},
	{d51STR1, d51STR2, d51STR3, d51STR4, d51STR5, d51STR6, d51STR7, d51WHL61, d51WHL62, d51WHL63, d51DEL},
}

var d51Coal = [d51Height + 1]string{
	coal01, coal02, coal03, coal04, coal05, coal06, coal07, coal08, coal09, coal10, coalDEL,
}

var c51Frames = [c51Patterns][c51Height + 1]string{
	{c51STR1, c51STR2, c51STR3, c51STR4, c51STR5, c51STR6, c51STR7, c51WH11, c51WH12, c51WH13, c51WH14, c51DEL},
	{c51STR1, c51STR2, c51STR3, c51STR4, c51STR5, c51STR6, c51STR7, c51WH21, c51WH22, c51WH23, c51WH24, c51DEL},
	{c51STR1, c51STR2, c51STR3, c51STR4, c51STR5, c51STR6, c51STR7, c51WH31, c51WH32, c51WH33, c51WH34, c51DEL},
	{c51STR1, c51STR2, c51STR3, c51STR4, c51STR5, c51STR6, c51STR7, c51WH41, c51WH42, c51WH43, c51WH44, c51DEL},
	{c51STR1, c51STR2, c51STR3, c51STR4, c51STR5, c51STR6, c51STR7, c51WH51, c51WH52, c51WH53, c51WH54, c51DEL},
	{c51STR1, c51STR2, c51STR3, c51STR4, c51STR5, c51STR6, c51STR7, c51WH61, c51WH62, c51WH63, c51WH64, c51DEL},
}

var c51Coal = [c51Height + 1]string{
	coalDEL, coal01, coal02, coal03, coal04, coal05, coal06, coal07, coal08, coal09, coal10, coalDEL,
}

var logoFrames = [logoPatterns][logoHeight + 1]string{
	{logo1, logo2, logo3, logo4, lwhl11, lwhl12, delLN},
	{logo1, logo2, logo3, logo4, lwhl21, lwhl22, delLN},
	{logo1, logo2, logo3, logo4, lwhl31, lwhl32, delLN},
	{logo1, logo2, logo3, logo4, lwhl41, lwhl42, delLN},
	{logo1, logo2, logo3, logo4, lwhl51, lwhl52, delLN},
	{logo1, logo2, logo3, logo4, lwhl61, lwhl62, delLN},
}

var logoCoal = [logoHeight + 1]string{lcoal1, lcoal2, lcoal3, lcoal4, lcoal5, lcoal6, delLN}
var logoCar  = [logoHeight + 1]string{lcar1, lcar2, lcar3, lcar4, lcar5, lcar6, delLN}

// ---------------------------------------------------------------------------
// Locomotive drawing routines (mirror C logic exactly)
// ---------------------------------------------------------------------------

func (cfg *Config) addD51(cv *Canvas, x int) {
	y := cfg.lines/2 - 5
	dy := 0
	if cfg.fly {
		y = x/7 + cfg.lines - cfg.cols/7 - d51Height
		dy = 1
	}
	pat := (d51Length + x) % d51Patterns
	for i := 0; i <= d51Height; i++ {
		cv.addStr(y+i, x, d51Frames[pat][i])
		cv.addStr(y+i+dy, x+53, d51Coal[i])
	}
	if cfg.accident {
		addMan(cv, y+2, x+43)
		addMan(cv, y+2, x+47)
	}
	if cfg.dance && !cfg.accident && !cfg.fly {
		addMDancer(cv, y-2, x+43)
		addFDancer(cv, y-2, x+48)
	}
	addSmoke(cv, y-1, x+d51Funnel)
}

func (cfg *Config) addC51(cv *Canvas, x int) {
	y := cfg.lines/2 - 5
	dy := 0
	if cfg.fly {
		y = x/7 + cfg.lines - cfg.cols/7 - c51Height
		dy = 1
	}
	pat := (c51Length + x) % c51Patterns
	for i := 0; i <= c51Height; i++ {
		cv.addStr(y+i, x, c51Frames[pat][i])
		cv.addStr(y+i+dy, x+55, c51Coal[i])
	}
	if cfg.accident {
		addMan(cv, y+3, x+45)
		addMan(cv, y+3, x+49)
	}
	if cfg.dance && !cfg.accident && !cfg.fly {
		addMDancer(cv, y-1, x+45)
		addFDancer(cv, y-1, x+50)
	}
	addSmoke(cv, y-1, x+c51Funnel)
}

func (cfg *Config) addSL(cv *Canvas, x int) {
	y := cfg.lines/2 - 3
	py1, py2, py3 := 0, 0, 0
	offset := 21
	if cfg.fly {
		y = x/6 + cfg.lines - cfg.cols/6 - logoHeight
		py1, py2, py3 = 2, 4, 6
	}
	pat := (logoLength + offset*(cfg.logo-1) + x) / 3 % logoPatterns
	for i := 0; i <= logoHeight; i++ {
		cv.addStr(y+i, x, logoFrames[pat][i])
		cv.addStr(y+i+py1, x+21, logoCoal[i])
		for j := 0; j <= cfg.logo; j++ {
			yoffset := 0
			if cfg.fly {
				yoffset = 2 * j
			}
			cv.addStr(y+i+py3+yoffset, x+42+offset*j, logoCar[i])
		}
	}
	if cfg.accident {
		addMan(cv, y+1, x+14)
		for j := 0; j <= cfg.logo; j++ {
			yoffset := 0
			if cfg.fly {
				yoffset = 2 + 2*j
			}
			addMan(cv, y+1+py2+yoffset, x+45+offset*j)
			addMan(cv, y+1+py2+yoffset, x+53+offset*j)
		}
	}
	if cfg.dance && !cfg.accident && !cfg.fly {
		addMDancer(cv, y-2, x+21)
		for j := 0; j <= cfg.logo; j++ {
			addMDancer(cv, y+py2-2, x+45+offset*j)
			addMDancer(cv, y+py2-2, x+50+offset*j)
			addMDancer(cv, y+py2-2, x+55+offset*j)
		}
	}
	addSmoke(cv, y-1, x+logoFunnel)
}

// ---------------------------------------------------------------------------
// Smoke
// ---------------------------------------------------------------------------

func addSmoke(cv *Canvas, y, x int) {
	if x%4 == 0 {
		for i := range smokeParticles {
			cv.addStr(smokeParticles[i].y, smokeParticles[i].x, smokeEraser[smokeParticles[i].ptrn])
			smokeParticles[i].y -= smokeDy[smokeParticles[i].ptrn]
			smokeParticles[i].x += smokeDx[smokeParticles[i].ptrn]
			if smokeParticles[i].ptrn < 15 {
				smokeParticles[i].ptrn++
			}
			cv.addStr(smokeParticles[i].y, smokeParticles[i].x, smokeStr[smokeParticles[i].kind][smokeParticles[i].ptrn])
		}
		n := len(smokeParticles)
		cv.addStr(y, x, smokeStr[n%2][0])
		smokeParticles = append(smokeParticles, smokeParticle{y: y, x: x, ptrn: 0, kind: n % 2})
	}
}

// ---------------------------------------------------------------------------
// People animations
// ---------------------------------------------------------------------------

var manFrames = [2][2]string{{"", "(O)"}, {"Help!", "\\O/"}}

func addMan(cv *Canvas, y, x int) {
	pat := (logoLength + x) / 12 % 2
	for i := 0; i < 2; i++ {
		cv.addStr(y+i, x, manFrames[pat][i])
	}
}

var fdancerFrames  = [2][3]string{{"\\\\0", "/\\", "|\\"}, {"0//", "/\\", "/|"}}
var efdancerFrames = [2][3]string{{"   ", "  ", "  "}, {"   ", "  ", "  "}}

func addFDancer(cv *Canvas, y, x int) {
	pat := (logoLength + x) / 12 % 2
	for i := 0; i < 3; i++ {
		cv.addStr(y+i, x+1, efdancerFrames[pat][i])
		cv.addStr(y+i, x, fdancerFrames[pat][i])
	}
}

var mdancerFrames  = [3][3]string{{"_O_", " #", "/\\"}, {"(0)", " #", "/\\"}, {"(O_", " #", "/\\"}}
var emdancerFrames = [3][3]string{{"   ", "  ", "  "}, {"   ", "  ", "  "}, {"   ", "  ", "  "}}

func addMDancer(cv *Canvas, y, x int) {
	pat := (logoLength + x) / 12 % 3
	for i := 0; i < 3; i++ {
		cv.addStr(y+i, x+1, emdancerFrames[pat][i])
		cv.addStr(y+i, x, mdancerFrames[pat][i])
	}
}

// ---------------------------------------------------------------------------
// Terminal size
// ---------------------------------------------------------------------------

func getTermSize() (cols, rows int) {
	cols, rows = 80, 24
	out, err := exec.Command("stty", "size").Output()
	if err == nil {
		parts := strings.Fields(strings.TrimSpace(string(out)))
		if len(parts) == 2 {
			r := atoi(parts[0])
			c := atoi(parts[1])
			if r > 0 && c > 0 {
				return c, r
			}
		}
	}
	return
}

func atoi(s string) int {
	n := 0
	for _, c := range s {
		if c < '0' || c > '9' {
			return 0
		}
		n = n*10 + int(c-'0')
	}
	return n
}

// ---------------------------------------------------------------------------
// CLI argument parsing
// ---------------------------------------------------------------------------

func parseArgs() Config {
	cfg := Config{}
	for _, arg := range os.Args[1:] {
		for i, ch := range arg {
			if i == 0 && ch == '-' {
				continue
			}
			switch ch {
			case 'a':
				cfg.accident = true
			case 'F':
				cfg.fly = true
			case 'l':
				cfg.logo++
			case 'c':
				cfg.c51 = true
			case 'd':
				cfg.dance = true
			case 'h':
				fmt.Println("sl — Steam Locomotive (Go port)")
				fmt.Println("Usage: sl [OPTIONS]")
				fmt.Println("  -a  accident mode (people on tracks)")
				fmt.Println("  -F  fly mode (locomotive lifts off screen)")
				fmt.Println("  -l  logo SL (small locomotive, repeat for more cars)")
				fmt.Println("  -c  C51 locomotive")
				fmt.Println("  -d  dance mode")
				os.Exit(0)
			}
		}
	}
	return cfg
}

// minX returns the leftmost x position (negative) that terminates the animation.
func minX(cfg Config) int {
	offset := 21
	if cfg.logo >= 1 {
		return -(logoLength + 1 + offset*(cfg.logo-1))
	}
	if cfg.c51 {
		return -(c51Length + 1)
	}
	return -(d51Length + 1)
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

func restoreTerminal() {
	fmt.Print("\x1b[?25h")     // show cursor
	fmt.Print("\x1b[0m")       // reset attributes
	fmt.Print("\x1b[2J\x1b[H") // clear screen
}

func main() {
	cfg := parseArgs()
	cfg.cols, cfg.lines = getTermSize()

	// Graceful exit on Ctrl-C / SIGTERM.
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
	go func() {
		<-sigCh
		restoreTerminal()
		os.Exit(0)
	}()

	fmt.Print("\x1b[?25l") // hide cursor
	fmt.Print("\x1b[2J")   // clear screen
	defer restoreTerminal()

	canvas := newCanvas(cfg.lines, cfg.cols)
	totalSteps := -minX(cfg) + cfg.cols - 1

	for step := 0; step < totalSteps; step++ {
		x := -step + cfg.cols - 1

		canvas.clear()

		if cfg.logo >= 1 {
			cfg.addSL(canvas, x)
		} else if cfg.c51 {
			cfg.addC51(canvas, x)
		} else {
			cfg.addD51(canvas, x)
		}

		canvas.flush()
		time.Sleep(40 * time.Millisecond)
	}
}
