#include <Python.h>

#include "demo/demo.h"

static PyObject *answer(PyObject *self, PyObject *args) { return PyLong_FromLong(demo_answer()); }

static PyMethodDef methods[] = {{"answer", answer, METH_NOARGS, NULL}, {NULL, NULL, 0, NULL}};

static struct PyModuleDef module = {PyModuleDef_HEAD_INIT, "extension", NULL, -1, methods};

PyMODINIT_FUNC PyInit_extension(void) { return PyModule_Create(&module); }
