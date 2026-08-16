#include <pybind11/pybind11.h>

int answer() {
    return 42;
}

PYBIND11_MODULE(extension, module) {
    module.def("answer", &answer);
}
