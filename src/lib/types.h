#ifndef __NECI_TYPES_H
#define __NECI_TYPEs_H

#include <stdint.h>

// By default we use double precision (8-bytes per real)
typedef double real_t;

// Are we using 32- or 64-bit integers?
#ifdef __INT64
typedef int64_t int_t;
typedef uint64_t uint_t;
#else
typedef int32_t int_t;
typedef uint32_t uint_t;
#endif

class complex_sp_t {
	float real;
	float imag;
};

class complex_dp_t {
	double real;
	double imag;
};

// A type(helement) equivalent
#ifdef __CMPLX
typedef complex_dp_t helement_t;
#else
typedef real_t helement_t;
#endif

// Just in case ...
extern "C" void stop_all (const char *, const char*);

#endif // __NECI_TYPES_H
