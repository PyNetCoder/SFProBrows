#include <string>
#include <algorithm>

#define DLLEXPORT __declspec(dllexport)

extern "C" {
    DLLEXPORT int kelime_kontrol(const char* girdi, const char* yasakli) {
        std::string str(girdi);
        std::string target(yasakli);
        
        if (str.find(target) != std::string::npos) {
            return 1; // Yasaklı kelime bulundu!
        }
        return 0;
    }
}