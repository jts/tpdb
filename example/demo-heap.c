#include <string.h>
#include <stdio.h>
#include <stdlib.h>

void f(int** p)
{
    int* q = malloc(sizeof(int) * 3);
    q[0] = 12;
    q[1] = -500;
    q[2] = 3737;
    *p = q;
}

int main()
{
    int* q;
    f(&q);
    free(q);
}
