#include <stdio.h>

struct point
{
    int x;
    int y;
};

int main()
{
    int arr[4] = { 323, 810, 12 };
    int n = sizeof(arr) / sizeof(arr[0]);
    struct point p = { -13, 25 };

    printf("arr size: %d\n", n);
}
