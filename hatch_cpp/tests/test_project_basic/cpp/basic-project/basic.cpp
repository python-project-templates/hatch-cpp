#include "basic-project/basic.hpp"

PyObject* hello(PyObject*, PyObject*) {
    return PyUnicode_FromString("A string");
}
