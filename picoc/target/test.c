#include <stdio.h>
void print_arr(int *p, int size) {
    for(int j = 0; j < size; j++) {
        printf("%d ", p[j]);
    }
    printf("\n");
}
int main() {
    int arr[] = { 1, 2, 3, 4 };
    print_arr(arr, 4);
    return 0;
}
