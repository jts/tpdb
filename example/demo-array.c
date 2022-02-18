#include <stdio.h>
#include <stdlib.h>

struct point
{
    int x;
    int y;
};

int sum(int x, int y) {
    return x + y;
}

int main()
{
    int arr[4] = { 323, 810, 12 };
    int n = sizeof(arr) / sizeof(arr[0]);
    struct point p = { -13, 25 };
    struct point* q = malloc(2 * sizeof(struct point));
    q[0].x = 1000;
    q[0].y = -8000;
    q[1].x = -871;
    q[1].y = 444;
    printf("arr size: %d\n", n);

    int (*func_ptr)(int, int) = sum;
    func_ptr(3, 2);
}
