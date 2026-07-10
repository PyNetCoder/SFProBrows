#include <string.h>
#define DLLEXPORT __declspec(dllexport)

DLLEXPORT int kontrol_et_guvenlik(const char* url) {
    if (strncmp(url, "https://", 8) == 0) {
        return 1; 
    }
    return 0;
}