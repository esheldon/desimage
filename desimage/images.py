import numpy as np
from numba import njit


@njit
def get_color_image(imr, img, imb, nonlinear, scales, colorim):
    """
    Create a color image.

    The idea here is that, after applying the asinh scaling, the color image
    should basically be between [0,1] for all filters.  Any place where a value
    is > 1 the intensity will be scaled back in all but the brightest filter
    but color preserved.

    In other words, you develaop a set of pre-scalings the images so that after
    multiplying by

        asinh(I/nonlinear)/(I/nonlinear)

    the numbers will be mostly between [0,1].  You can send scales using the
    scale= keyword

    It can actually be good to have some color saturation so don't be too
    agressive.  You'll have to play with the numbers for each image.

    Note also the image is clipped at zero.

    TODO:
        Implement a "saturation" level in the raw image values as in
        djs_rgb_make.  Even better, implement an outside function to do this.
    """

    nrows,ncols = imr.shape

    fac=1./nonlinear/3.

    for row in range(nrows):
        for col in range(ncols):
            rval = imr[row,col] * scales[0]
            gval = img[row,col] * scales[1]
            bval = imb[row,col] * scales[2]

            if rval < 0.0:
                rval=0.0
            if gval < 0.0:
                gval=0.0
            if bval < 0.0:
                bval=0.0

            # average images and divide by the nonlinear factor
            meanval = (rval + gval + bval)/3.0
            I = meanval/nonlinear

            if I <= 0.0:
                I = 1.0/3.0

            f = np.arcsinh(I)/I

            if (rval*f > 1) or (gval*f > 1) or (bval*f > 1):
                maxval = max(rval, gval, bval)
                if maxval > 0.0: 
                    f = 1.0/maxval

            colorim[row,col,0] = rval*f
            colorim[row,col,1] = gval*f
            colorim[row,col,2] = bval*f

@njit
def interpolate_bad(im, mask):
    """
    go along columns until we hit a problem, then continue
    the last value
    """
    nrows,ncols = im.shape

    for col in range(ncols):
        last_good=0
        have_good=False
        for row in range(nrows):
            if mask[row,col] > 0:
                # we hit a bad value
                if have_good:
                    # we have a good value to continue
                    im[row,col] = last_good
            else:
                last_good = im[row,col]
                have_good=True


@njit
def propagate_missing_data(im1, im2, im3, mask):
    """
    If the data are masked because of missing data, just set
    all images to zero there to avoid odd colors.

    Update the mask so we won't interpolate
    """
    nrows,ncols = im1.shape

    for col in range(ncols):
        for row in range(nrows):
            if mask[row,col] > 0:
                v1 = im1[row,col]
                v2 = im2[row,col]
                v3 = im3[row,col]

                if v1==0.0 or v2==0.0 or v3==0.0:
                    im1[row,col] = 0.0
                    im2[row,col] = 0.0
                    im3[row,col] = 0.0
                    mask[row,col] = 0


def bytescale(im):
    """ 
    The input should be between [0,1]

    output is [0,255] in a unsigned byte array
    """
    imout = (im*255).astype('u1')
    return imout

def boost( a, factor):
    """
    Resize an array to larger shape, simply duplicating values.
    """
    
    factor=int(factor)
    if factor < 1:
        raise ValueError("boost factor must be >= 1")

    newshape=np.array(a.shape)*factor

    slices = [ slice(0,old, float(old)/new) for old,new in zip(a.shape,newshape) ]
    coordinates = np.mgrid[slices]
    indices = coordinates.astype('i')   #choose the biggest smaller integer index
    return a[tuple(indices)]

def rebin(im, factor, dtype=None):
    """
    Rebin the image so there are fewer pixels.  The pixels are simply
    averaged.
    """
    factor=int(factor)
    s = im.shape
    if ( (s[0] % factor) != 0
            or (s[1] % factor) != 0):
        raise ValueError("shape in each dim (%d,%d) must be "
                   "divisible by factor (%d)" % (s[0],s[1],factor))

    newshape=np.array(s)/factor
    if dtype is None:
        a=im
    else:
        a=im.astype(dtype)

    return a.reshape(newshape[0],factor,newshape[1],factor,).sum(1).sum(2)/factor/factor

'''
def _fix_hard_satur(r, g, b, satval):
    """
    Clip to satval but preserve the color
    """

    # make sure you send scales such that this occurs at 
    # a reasonable place for your images

    maximage=_get_max_image(r,g,b)

    w=np.where(maximage > satval)
    if w[0].size > 1:
        # this preserves color
        fac=satval/maximage[w]
        r[w] *= fac
        g[w] *= fac
        b[w] *= fac
        maximage[w]=satval

    return maximage

def _fix_rgb_satur(r,g,b,fac):
    """
    Fix the factor so we don't saturate the
    RGB image (> 1)

    maximage is the
    """
    maximage=_get_max_image(r,g,b)

    w=np.where( (r*fac > 1) | (g*fac > 1) | (b*fac > 1) )
    if w[0].size > 1:
        # this preserves color
        fac[w]=1.0/maximage[w]


def _get_max_image(im1, im2, im3):
    maximage=im1.copy()

    w=np.where(im2 > maximage)
    if w[0].size > 1:
        maximage[w] = im2[w]

    w=np.where(im3 > maximage)
    if w[0].size > 1:
        maximage[w] = im3[w]

    return maximage


def get_color_image_old(imr, img, imb, **keys):
    """
    Create a color image.

    The idea here is that, after applying the asinh scaling, the color image
    should basically be between [0,1] for all filters.  Any place where a value
    is > 1 the intensity will be scaled back in all but the brightest filter
    but color preserved.

    In other words, you develaop a set of pre-scalings the images so that after
    multiplying by

        asinh(I/nonlinear)/(I/nonlinear)

    the numbers will be mostly between [0,1].  You can send scales using the
    scale= keyword

    It can actually be good to have some color saturation so don't be too
    agressive.  You'll have to play with the numbers for each image.

    Note also the image is clipped at zero.

    TODO:
        Implement a "saturation" level in the raw image values as in
        djs_rgb_make.  Even better, implement an outside function to do this.
    """

    nonlinear=keys.get('nonlinear',1.0)
    scales=keys.get('scales',None)
    satval=keys.get('satval',None)

    r = imr.astype('f4')
    g = img.astype('f4')
    b = imb.astype('f4')

    r.clip(0.,r.max(),r)
    g.clip(0.,g.max(),g)
    b.clip(0.,b.max(),b)

    if scales is not None:
        r *= scales[0]
        g *= scales[1]
        b *= scales[2]

    if satval is not None:
        # note using rescaled images so the satval
        # means the same thing (e.g. in terms of real flux)
        maximage=_fix_hard_satur(r,g,b,satval)


    # average images and divide by the nonlinear factor
    fac=1./nonlinear/3.
    I = fac*(r + g + b)

    # make sure we don't divide by zero
    # due to clipping, average value is zero only if all are zero
    w=np.where(I <= 0)
    if w[0].size > 0:
        I[w] = 1./3. # value doesn't matter images are zero

    f = np.arcsinh(I)/I

    # limit to values < 1
    # make sure you send scales such that this occurs at 
    # a reasonable place for your images
    _fix_rgb_satur(r,g,b,f)

    R = r*f
    G = g*f
    B = b*f

    st=R.shape
    colorim=np.zeros( (st[0], st[1], 3) )

    colorim[:,:,0] = R[:,:]
    colorim[:,:,1] = G[:,:]
    colorim[:,:,2] = B[:,:]

    return colorim

'''
