#include <string.h>
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <wchar.h>

#define WIDTH 80
#define HEIGHT 40
#define MAX_DROPS 120

typedef struct
{
    int x;
    int y;
    int length;
    int speed;
} Drop;

Drop drops[MAX_DROPS];

const wchar_t MATRIX_CHARS[] =
{
    L'0',L'1',L'2',L'3',L'4',
    L'5',L'6',L'7',L'8',L'9',

    L'@',L'#',L'%',L'&',L'*',
    L'+',L'-',L'=',L'?',L'!',

    0x30A2,0x30A4,0x30A6,0x30A8,0x30AA,
    0x30AB,0x30AD,0x30AF,0x30B1,0x30B3,
    0x30B5,0x30B7,0x30B9,0x30BB,0x30BD,
    0x30BF,0x30C1,0x30C4,0x30C6,0x30C8,
    0x30CA,0x30CB,0x30CC,0x30CD,0x30CE,
    0x30CF,0x30D2,0x30D5,0x30D8,0x30DB,
    0x30DE,0x30DF,0x30E0,0x30E1,0x30E2,
    0x30E4,0x30E6,0x30E8,
    0x30E9,0x30EA,0x30EB,0x30EC,0x30ED,
    0x30EF,0x30F2,0x30F3
};

const int CHAR_COUNT =
sizeof(MATRIX_CHARS) /
sizeof(MATRIX_CHARS[0]);

HANDLE console;

DWORD written;

void ansi(const char *s)
{
    WriteConsoleA(
        console,
        s,
        (DWORD)strlen(s),
        &written,
        NULL
    );
}

void putChar(wchar_t c)
{
    WriteConsoleW(
        console,
        &c,
        1,
        &written,
        NULL
    );
}

void gotoXY(int x,int y)
{
    COORD c;
    c.X=(SHORT)x;
    c.Y=(SHORT)y;
    SetConsoleCursorPosition(console,c);
}

void hideCursor()
{
    CONSOLE_CURSOR_INFO ci;

    ci.dwSize=1;
    ci.bVisible=FALSE;

    SetConsoleCursorInfo(console,&ci);
}

void clearScreen()
{
    ansi("\x1b[2J");
}

void initDrops()
{
    for(int i=0;i<MAX_DROPS;i++)
    {
        drops[i].x=rand()%WIDTH;
        drops[i].y=-(rand()%HEIGHT);

        drops[i].length=
            5+
            rand()%20;

        drops[i].speed=
            1+
            rand()%3;
    }
}

wchar_t randomChar()
{
    return MATRIX_CHARS[
        rand()%CHAR_COUNT
    ];
}

void setColor(int index)
{
    char buffer[32];

    sprintf(
        buffer,
        "\x1b[38;5;%dm",
        index
    );

    ansi(buffer);
}
void drawDrop(Drop *d)
{
    for(int i=0;i<d->length;i++)
    {
        int yy=d->y-i;

        if(yy<0 || yy>=HEIGHT)
            continue;

        gotoXY(d->x,yy);

        if(i==0)
        {
            setColor(15);
        }
        else if(i<2)
        {
            setColor(120);
        }
        else if(i<5)
        {
            setColor(82);
        }
        else if(i<10)
        {
            setColor(34);
        }
        else
        {
            setColor(22);
        }

        putChar(randomChar());
    }

    int tail=d->y-d->length;

    if(tail>=0 && tail<HEIGHT)
    {
        gotoXY(d->x,tail);
        ansi("\x1b[0m ");
    }
}

void updateDrops()
{
    for(int i=0;i<MAX_DROPS;i++)
    {
        drawDrop(&drops[i]);

        drops[i].y+=drops[i].speed;

        if(drops[i].y-drops[i].length>HEIGHT)
        {
            drops[i].x=rand()%WIDTH;
            drops[i].y=-(rand()%HEIGHT);

            drops[i].length=
                5+
                rand()%20;

            drops[i].speed=
                1+
                rand()%3;
        }
    }
}

void enableANSI()
{
    HANDLE out=GetStdHandle(STD_OUTPUT_HANDLE);

    DWORD mode=0;

    GetConsoleMode(out,&mode);

    mode|=ENABLE_VIRTUAL_TERMINAL_PROCESSING;

    SetConsoleMode(out,mode);
}

void resizeConsole()
{
    SMALL_RECT rect;

    rect.Left=0;
    rect.Top=0;
    rect.Right=WIDTH-1;
    rect.Bottom=HEIGHT-1;

    SetConsoleWindowInfo(
        console,
        TRUE,
        &rect
    );

    COORD size;

    size.X=WIDTH;
    size.Y=HEIGHT;

    SetConsoleScreenBufferSize(
        console,
        size
    );
}
int main(void)
{
    srand((unsigned)time(NULL));

    console = GetStdHandle(STD_OUTPUT_HANDLE);

    enableANSI();

    hideCursor();

    resizeConsole();

    clearScreen();

    initDrops();

    while(1)
    {
        updateDrops();

        Sleep(40);
    }

    ansi("\x1b[0m");

    return 0;
}