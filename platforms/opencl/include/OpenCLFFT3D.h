#ifndef __OPENMM_OPENCLFFT3D_H__
#define __OPENMM_OPENCLFFT3D_H__

/* -------------------------------------------------------------------------- *
 *                                   OpenMM                                   *
 * -------------------------------------------------------------------------- *
 * This is part of the OpenMM molecular simulation toolkit originating from   *
 * Simbios, the NIH National Center for Physics-Based Simulation of           *
 * Biological Structures at Stanford, funded under the NIH Roadmap for        *
 * Medical Research, grant U54 GM072970. See https://simtk.org.               *
 *                                                                            *
 * Portions copyright (c) 2009-2025 Stanford University and the Authors.      *
 * Authors: Peter Eastman                                                     *
 * Contributors:                                                              *
 *                                                                            *
 * This program is free software: you can redistribute it and/or modify       *
 * it under the terms of the GNU Lesser General Public License as published   *
 * by the Free Software Foundation, either version 3 of the License, or       *
 * (at your option) any later version.                                        *
 *                                                                            *
 * This program is distributed in the hope that it will be useful,            *
 * but WITHOUT ANY WARRANTY; without even the implied warranty of             *
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the              *
 * GNU Lesser General Public License for more details.                        *
 *                                                                            *
 * You should have received a copy of the GNU Lesser General Public License   *
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.      *
 * -------------------------------------------------------------------------- */

#define USE_VKFFT

#ifdef USE_VKFFT
#define VKFFT_BACKEND 3
#pragma clang diagnostic ignored "-Wdeprecated-declarations"
#include "vkFFT.h"
#endif
#include "openmm/common/FFT3D.h"
#include "openmm/common/ArrayInterface.h"

namespace OpenMM {

class OpenCLContext;

#ifdef USE_VKFFT
/**
 * This class performs three dimensional Fast Fourier Transforms.  It uses the
 * VkFFT library (https://github.com/DTolm/VkFFT).
 *
 * This class is most efficient when the size of each dimension is a product of
 * small prime factors: 2, 3, 5, 7, 11, and 13.  You can call findLegalDimension()
 * to determine the smallest size that satisfies this requirement and is greater
 * than or equal to a specified minimum size.
 *
 * Note that this class performs an unnormalized transform.  That means that if you perform
 * a forward transform followed immediately by an inverse transform, the effect is to
 * multiply every value of the original data set by the total number of data points.
 */
#else
/**
 * This class performs three dimensional Fast Fourier Transforms.  It is based on the
 * mixed radix algorithm described in
 *
 * Takahashi, D. and Kanada, Y., "High-Performance Radix-2, 3 and 5 Parallel 1-D Complex
 * FFT Algorithms for Distributed-Memory Parallel Computers."  Journal of Supercomputing,
 * 15, 207–228 (2000).
 *
 * This class places certain restrictions on the allowed dimensions of the grid.  First,
 * the size of each dimension may have no prime factors other than 2, 3, 5, and 7.  You
 * can call findLegalDimension() to determine the smallest size that satisfies this
 * requirement and is greater than or equal to a specified minimum size.  Second, the size
 * of each dimension must be small enough to compute each 1D transform entirely in local
 * memory with one work unit per data point.  This will vary between platforms, but is
 * typically at least 512.
 *
 * Note that this class performs an unnormalized transform.  That means that if you perform
 * a forward transform followed immediately by an inverse transform, the effect is to
 * multiply every value of the original data set by the total number of data points.
 */
#endif

class OPENMM_EXPORT_COMMON OpenCLFFT3D : public FFT3D {
public:
    /**
     * Create an OpenCLFFT3D object for performing transforms of a particular size.
     *
     * @param context the context in which to perform calculations
     * @param xsize   the first dimension of the data sets on which FFTs will be performed
     * @param ysize   the second dimension of the data sets on which FFTs will be performed
     * @param zsize   the third dimension of the data sets on which FFTs will be performed
     * @param realToComplex  if true, a real-to-complex transform will be done.  Otherwise, it is complex-to-complex.
     */
    OpenCLFFT3D(OpenCLContext& context, int xsize, int ysize, int zsize, bool realToComplex=false);
#ifdef USE_VKFFT
    ~OpenCLFFT3D();
#endif
    /**
     * Perform a Fourier transform.  The transform cannot be done in-place: the input and output
     * arrays must be different.  Also, the input array is used as workspace, so its contents
     * are destroyed.  This also means that both arrays must be large enough to hold complex values,
     * even when performing a real-to-complex transform.
     *
     * When performing a real-to-complex transform, the output data is of size xsize*ysize*(zsize/2+1)
     * and contains only the non-redundant elements.
     *
     * @param in       the data to transform, ordered such that in[x*ysize*zsize + y*zsize + z] contains element (x, y, z)
     * @param out      on exit, this contains the transformed data
     * @param forward  true to perform a forward transform, false to perform an inverse transform
     */
    void execFFT(ArrayInterface& in, ArrayInterface& out, bool forward=true);
    /**
     * Get the smallest legal size for a dimension of the grid (that is, a size with no unsupported
     * prime factors).
     *
     * @param minimum   the minimum size the return value must be greater than or equal to
     */
    static int findLegalDimension(int minimum);
private:
    int xsize, ysize, zsize;
    int xthreads, ythreads, zthreads;
    bool packRealAsComplex;
    OpenCLContext& context;
#ifdef USE_VKFFT
    VkFFTApplication app;
#else
    cl::Kernel createKernel(int xsize, int ysize, int zsize, int& threads, int axis, bool forward, bool inputIsReal);
    cl::Kernel xkernel, ykernel, zkernel;
    cl::Kernel invxkernel, invykernel, invzkernel;
    cl::Kernel packForwardKernel, unpackForwardKernel, packBackwardKernel, unpackBackwardKernel;
#endif
};

} // namespace OpenMM

#endif // __OPENMM_OPENCLFFT3D_H__
