import cv2
import collections
import numpy as np
import pylab as plt
from jterator import jtapi


def threshold(InputImage, RescaleValue=0.00390625, CorrectionFactor=1,
              MinValue=None, MaxValue=None, **kwargs):
    '''
    Jterator module for thresholding an image with Otsu's method.
    For more information see `opencv docs <http://opencv-python-tutroals.readthedocs.org/en/latest/py_tutorials/py_imgproc/py_thresholding/py_thresholding.html#otsus-binarization>`_.

    .. warning::

        The image is casted to 8-bit before thresholding is applied.
        if `InputImage` is not 8-bit, it's assumed that it is is 16-bit
        by default. If `InputImage` has a different range of pixel values
        set `RescaleValue` accordingly.

    Parameters
    ----------
    InputImage: numpy.ndarray
        grayscale image that should be thresholded
    RescaleValue: int, optional
        value by which `InputImage` is multiplied before conversion to 8-bit
        (e.g. if the image has dtype "float64" with values between 0 and 1
        it has to be multiplied by 255; defaults to 1/256 = 0.00390625
        assuming that `InputImage` is 16-bit)
    CorrectionFactor: int, optional
        value by which the calculated threshold value will be multiplied
    MinValue: int, optional
        minimal threshold value (in the non-rescaled `InputImage`)
    MaxValue: int, optional
        maximal threshold value (in the non-rescaled `InputImage`)
    **kwargs: dict
        additional arguments provided by Jterator:
        "ProjectDir", "DataFile", "FigureFile", "Plot"

    Returns
    -------
    namedtuple[numpy.ndarray[bool]]
        binary thresholded image: "ThresholdedImage"

    Raises
    ------
    ValueError
        when all pixel values of `InputImage` are zero after rescaling
    '''
    if MaxValue is None:
        MaxValue = np.max(InputImage)
    if MinValue is None:
        MinValue = np.min(InputImage)

    # opencv function requires 8-bit image
    if InputImage.dtype != 'uint8':
        InputImage = np.array(InputImage * RescaleValue, dtype=np.uint8)
        MaxValue = MaxValue * RescaleValue
        MinValue = MinValue * RescaleValue

    if (InputImage == 0).all():
        raise ValueError('All pixel values are 0.'
                         'Something went wrong during casting to 8-bit.')

    img, thresh = cv2.threshold(InputImage, 0, 255,
                                cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    thresh = thresh * CorrectionFactor

    if thresh > MaxValue:
        thresh = MaxValue
    elif thresh < MinValue:
        thresh = MinValue

    img = InputImage > thresh

    if kwargs['Plot']:

        fig = plt.figure(figsize=(10, 10))
        ax1 = fig.add_subplot(1, 2, 1)
        ax2 = fig.add_subplot(1, 2, 2)

        ax1.imshow(InputImage, cmap='gray',
                   vmin=np.percentile(InputImage, 0.1),
                   vmax=np.percentile(InputImage, 99.9))
        ax1.set_title('InputImage', size=20)

        ax2.imshow(img)
        ax2.set_title('ThresholdedImage', size=20)

        fig.tight_layout()

        jtapi.savefigure(fig, kwargs['FigureFile'])

    output = collections.namedtuple('Output', 'ThresholdedImage')
    return output(img)
