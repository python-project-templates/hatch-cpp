#pragma once
#include <pybind11/pybind11.h>
#include <string>

std::string hello();

PYBIND11_MODULE(extension, m) {
    m.def("hello", &hello);
}