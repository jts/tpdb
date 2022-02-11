#include <stdio.h>
#include <stdlib.h>
#include <string.h>

char* remove_ext(char* s, char* ext)
{
    char* p = strstr(s, ext);
    int n = p - s;
    char* out = malloc(n + 1);
    strncpy(out, s, n);
    out[n] = '\0';
    return out;
}

int main()
{
    char* input = "example.txt";
    char test[] = "literal?";
    char* output = remove_ext(input, ".txt");
    puts(output);
    puts(test);
}
