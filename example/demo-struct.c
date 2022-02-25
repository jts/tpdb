#include <stdio.h>
#include <stdlib.h>

struct point
{
    int x;
    int y;
};

int main()
{
    int n = 2;
    struct point* p = malloc(n * sizeof(struct point));
    p[0].x = 1000;
    p[0].y = -8000;
    p[1].x = -871;
    p[1].y = 444;
}
