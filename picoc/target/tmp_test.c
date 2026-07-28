#include <stdio.h>
int main() {
    double d = 176.45600000000002;
    int x = (int)d;
    float f = (float)x;
    printf("double: %.3f, cast_int: %d, cast_float: %.1f\n", d, x, f);
    
    unsigned char uc = 250;
    int promoted = uc + 53;
    printf("promoted: %d\n", promoted);
    return 0;
}
