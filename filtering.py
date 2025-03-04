import cv2
import copy
import numpy as np

def cross_correlation_2d(img, kernel):
    '''Given a kernel of arbitrary m x n dimensions, with both m and n being
    odd, compute the cross correlation of the given image with the given
    kernel, such that the output is of the same dimensions as the image and that
    you assume the pixels out of the bounds of the image to be zero. Note that
    you need to apply the kernel to each channel separately, if the given image
    is an RGB image.

    Inputs:
        img:    Either an RGB image (height x width x 3) or a grayscale image
                (height x width) as a numpy array.
        kernel: A 2D numpy array (m x n), with m and n both odd (but may not be
                equal).

    Output:
        Return an image of the same dimensions as the input image (same width,
        height and the number of color channels)
    '''
    
    img_dim = img.ndim
    out_img = np.zeros_like(img, dtype='float64')
    
    if (img_dim == 2):
        img_h, img_w = img.shape
        half_m, half_n = kernel.shape
        full_m = half_m
        full_n = half_n
        half_m //= 2
        half_n //= 2
        img_pad = np.pad(img, ((half_m,half_m),(half_n,half_n)), mode='constant')
        
        for h in range(img_h):
            for w in range(img_w):
                out_img[h,w] = np.sum(kernel * img_pad[h:(h+full_m),w:(w+full_n)])
    elif (img_dim == 3):
        img_h = img.shape[0]
        img_w = img.shape[1]
        half_m, half_n = kernel.shape
        full_m = half_m
        full_n = half_n
        half_m //= 2
        half_n //= 2
        img_pad = np.pad(img, ((half_m,half_m),(half_n,half_n),(0,0)), mode='constant')
        
        for h in range(img_h):
            for w in range(img_w):
                out_img[h,w,0] = np.sum(kernel * img_pad[h:(h+full_m),w:(w+full_n),0])
                out_img[h,w,1] = np.sum(kernel * img_pad[h:(h+full_m),w:(w+full_n),1])
                out_img[h,w,2] = np.sum(kernel * img_pad[h:(h+full_m),w:(w+full_n),2])
            
    return out_img

def convolve_2d(img, kernel):
    '''Use cross_correlation_2d() to carry out a 2D convolution.

    Inputs:
        img:    Either an RGB image (height x width x 3) or a grayscale image
                (height x width) as a numpy array.
        kernel: A 2D numpy array (m x n), with m and n both odd (but may not be
                equal).

    Output:
        Return an image of the same dimensions as the input image (same width,
        height and the number of color channels)
    '''
    kernel = kernel[::-1,::-1]
    return cross_correlation_2d(img,kernel)

def gaussian_blur_kernel_2d(sigma, height, width):
    '''Return a Gaussian blur kernel of the given dimensions and with the given
    sigma. Note that width and height may be different, but sigma applies to
    both dimensions. Normalize the kernel so it sums to 1.

    Input:
        sigma:  The parameter that controls the radius of the Gaussian blur.
                Note that, in our case, it is a circular Gaussian (symmetric
                across height and width).
        width:  The width of the kernel.
        height: The height of the kernel.

    Output:
        Return a kernel of dimensions height x width such that convolving it
        with an image results in a Gaussian-blurred image.
    '''
    
    e = np.e
    pi = np.pi
    half_height = height // 2
    half_width = width // 2

    filter = np.zeros((height,width))
    
    for y in range(height):
        for x in range(width):
            filter[y,x] = (1/(2*pi*sigma))*(e**(-((x-half_width)**2+(y-half_height)**2)/(2*sigma**2)))

    norm_filter = filter / np.sum(filter)

    return norm_filter


def low_pass(img, sigma, size):
    '''Filter the image as if its filtered with a low pass filter of the given
    sigma and a square kernel of the given size. A low pass filter supresses
    the higher frequency components (finer details) of the image.

    Output:
        Return an image of the same dimensions as the input image (same width,
        height and the number of color channels)
    '''
    
    return convolve_2d(img, gaussian_blur_kernel_2d(sigma, size, size))

def high_pass(img, sigma, size):
    '''Filter the image as if its filtered with a high pass filter of the given
    sigma and a square kernel of the given size. A high pass filter suppresses
    the lower frequency components (coarse details) of the image.

    Output:
        Return an image of the same dimensions as the input image (same width,
        height and the number of color channels)
    '''
    return img - convolve_2d(img, gaussian_blur_kernel_2d(sigma, size, size))

def create_hybrid_image(img1, img2, sigma1, size1, high_low1, sigma2, size2,
        high_low2, mixin_ratio):
    '''This function adds two images to create a hybrid image, based on
    parameters specified by the user.'''
    high_low1 = high_low1.lower()
    high_low2 = high_low2.lower()

    if img1.dtype == np.uint8:
        img1 = img1.astype(np.float32) / 255.0
        img2 = img2.astype(np.float32) / 255.0

    if high_low1 == 'low':
        img1 = low_pass(img1, sigma1, size1)
    else:
        img1 = high_pass(img1, sigma1, size1)

    if high_low2 == 'low':
        img2 = low_pass(img2, sigma2, size2)
    else:
        img2 = high_pass(img2, sigma2, size2)

    img1 *= 2 * (1 - mixin_ratio)
    img2 *= 2 * mixin_ratio
    hybrid_img = (img1 + img2)
    return (hybrid_img * 255).clip(0, 255).astype(np.uint8)

# seperable filter borrowed from Scott Wehrwein's lecture code
def separable_filter(img, kernel1d):
    return cross_correlation_2d(cross_correlation_2d(img, kernel1d), kernel1d.T)

def construct_laplacian(img, levels):
    """ Construct a Laplacian pyramid for the image img with `levels` levels.
    Returns a python list; the first `levels`-1 elements are high-pass images
    each one half the size of the previous; the last one is the remaining
    low-pass image.
    Precondition: img has dimensions HxW[xC], and H and W are each divisible
    by 2**(levels-1) """

    h, w = img.shape[:2]
    f = 2**(levels-1) # power of two that the dimensions must be divisible by
    assert h % f == 0 and w % f == 0
    
    blur_1d = np.array([0.0625, 0.25, 0.375, 0.25, 0.0625]).reshape((1, 5))
    gau_pyr = []
    gau_pyr.append(img)
    
    # generate gaussian pyramid
    for currLev in range(1,levels):
        blurImg = separable_filter(gau_pyr[currLev-1], blur_1d)
        blurImg = blurImg[::2,::2,:]
        gau_pyr.append(blurImg)
        
    lap_pyr = []
    lap_pyr.append(gau_pyr[levels-1])
    
    # generate laplacian pyramid from gaussian pyramid
    for currLev in range(levels-1,0,-1):
        currImg = gau_pyr[currLev]
        H, W, = currImg.shape[:2]
        upImg = np.zeros((2*H, 2*W, 3), dtype=img.dtype)    # nearest neighbor code from lecture code
        for (io, jo) in ((0, 0), (0, 1), (1, 0), (1, 1)):   # created by scott wehrwein
                upImg[io::2, jo::2, :] = currImg
        lap_pyr.insert(0, gau_pyr[currLev-1] - upImg)
        
    return lap_pyr

def reconstruct_laplacian(pyr, weights=None):
    """ Given a laplacian pyramid, reconstruct the original image.
    `pyr` is a list of pyramid levels following the spec produced by
        `construct_laplacian`
    `weights` is either None or a list of floats whose length is len(pyr)
        If weights is not None, scale each level of the pyramid by its
        corresponding value in the weights list while adding it into the 
        reconstruction.
    """
    
    # create copy as to not damage underlying laplacian representation
    copy_pyr = copy.deepcopy(pyr)
    
    levels = len(copy_pyr)
    
    finalH, finalW, = copy_pyr[levels-1].shape[:2]   
    finalImg = np.zeros((finalH, finalW), dtype=copy_pyr[0].dtype)
    
    if weights is None:
        for currLev in range(levels-1,0,-1):
            currImg = copy_pyr[currLev]
            H, W, = currImg.shape[:2]
            upImg = np.zeros((2*H, 2*W, 3), dtype=copy_pyr[0].dtype)
            for (io, jo) in ((0, 0), (0, 1), (1, 0), (1, 1)):   # nearest neighbor code from lecture code
                    upImg[io::2, jo::2, :] = currImg            # created by scott wehrwein
            copy_pyr[currLev-1] += upImg 
    else:
        # multiple layers by weights
        for lev in range(levels):
            copy_pyr[lev] *= weights[lev]
        # reconstruct image
        for currLev in range(levels-1,0,-1):
            currImg = copy_pyr[currLev]
            H, W, = currImg.shape[:2]
            upImg = np.zeros((2*H, 2*W, 3), dtype=copy_pyr[0].dtype)
            for (io, jo) in ((0, 0), (0, 1), (1, 0), (1, 1)):
                    upImg[io::2, jo::2, :] = currImg
            copy_pyr[currLev-1] += upImg
                
    return copy_pyr[0]
            

