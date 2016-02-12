from tmlib.writers import ImageWriter


def save_image(image, filename, **kwargs):
    '''
    Jterator module for saving images that only exist in memory but not on disk.

    Parameters
    ----------
    image: numpy.ndarray
        image that should be saved
    filename: str
        absolute path to a file, where the image should be saved
    **kwargs: dict
        additional arguments provided by Jterator:
        "data_file", "figure_file", "experiment_dir", "plot", "job_id"
    '''
    with ImageWriter() as writer:
        writer.write(filename, image)
