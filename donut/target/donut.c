#include <stdio.h>
#include <math.h>
#include <string.h>

#ifdef _WIN32
#include <windows.h>
static void frame_sleep(unsigned int milliseconds) {
    Sleep(milliseconds);
}
#else
#include <unistd.h>
static void frame_sleep(unsigned int milliseconds) {
    usleep(milliseconds * 1000);
}
#endif

#define SCREEN_WIDTH  80
#define SCREEN_HEIGHT 22
#define BUFFER_SIZE   (SCREEN_WIDTH * SCREEN_HEIGHT)

static const char LUMINANCE_RAMP[] = ".,-~:;=!*#$@";

typedef struct {
    char pixels[BUFFER_SIZE];
    double z_buffer[BUFFER_SIZE];
} FrameBuffer;

static void framebuffer_clear(FrameBuffer *fb) {
    memset(fb->pixels, ' ', BUFFER_SIZE);
    memset(fb->z_buffer, 0, sizeof(fb->z_buffer));
}

static void render_frame(FrameBuffer *fb, double angle1, double angle2) {
    double sin_angle1 = sin(angle1);
    double cos_angle1 = cos(angle1);
    double sin_angle2 = sin(angle2);
    double cos_angle2 = cos(angle2);

    for (int j = 0; j < 628; j += 7) {
        double phi = (double)j / 100.0;
        double sin_j = sin(phi);
        double cos_j = cos(phi);
        double height = cos_j + 2.0;

        for (int i = 0; i < 628; i += 2) {
            double theta = (double)i / 100.0;
            double sin_i = sin(theta);
            double cos_i = cos(theta);

            double distance = 1.0 / (sin_i * height * sin_angle1 + sin_j * cos_angle1 + 5.0);
            double sin_height = sin_i * height * cos_angle1 - sin_j * sin_angle1;

            int x = (int)(40.0 + 30.0 * distance * (cos_i * height * cos_angle2 - sin_height * sin_angle2));
            int y = (int)(12.0 + 15.0 * distance * (cos_i * height * sin_angle2 + sin_height * cos_angle2));

            int index = x + SCREEN_WIDTH * y;

            int brightness = (int)(8.0 * ((sin_j * sin_angle1 - sin_i * cos_j * cos_angle1) * cos_angle2 
                                        - sin_i * cos_j * sin_angle1 
                                        - sin_j * cos_angle1 
                                        - cos_i * cos_j * sin_angle2));

            if (y >= 0 && y < SCREEN_HEIGHT && x >= 0 && x < SCREEN_WIDTH && distance > fb->z_buffer[index]) {
                fb->z_buffer[index] = distance;
                int ramp_idx = brightness > 0 ? brightness : 0;
                if (ramp_idx >= 12) {
                    ramp_idx = 11;
                }
                fb->pixels[index] = LUMINANCE_RAMP[ramp_idx];
            }
        }
    }
}

static void display_frame(const FrameBuffer *fb) {
    fputs("\033[H", stdout);
    fwrite(fb->pixels, sizeof(char), BUFFER_SIZE, stdout);
    fflush(stdout);
}

int main(void) {
    FrameBuffer fb;
    double angle1 = 0.0;
    double angle2 = 0.0;

    fputs("\033[2J", stdout);
    fflush(stdout);

    while (1) {
        framebuffer_clear(&fb);
        render_frame(&fb, angle1, angle2);
        display_frame(&fb);

        angle1 += 0.30;
        angle2 += 0.15;

        frame_sleep(30);
    }

    return 0;
}
