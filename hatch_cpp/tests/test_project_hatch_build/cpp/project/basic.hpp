#pragma once
#include <nanobind/nanobind.h>
#include <nanobind/stl/string.h>

NB_MODULE(extension, m) {
    m.def("hello", []() { return "A string"; });
}
