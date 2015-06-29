import os
import natsort
import h5py
import numpy as np
from scipy import misc
import tmt
import image_registration


def calculate_shift(filename, ref_filename):
    '''
    Calculate shift between two images based on fast Fourier transform.

    "Apparently astronomical images look a lot like microscopic images." [1]_

    Parameters
    ----------
    filename: str
        path to image that should be registered

    ref_filename: str
        path to image that should be used as a reference

    Returns
    -------
    Tuple[int]
        shift in x, y direction

    References
    ----------
    .. [1] http://image-registration.readthedocs.org/en/latest/
    '''
    # Load image that should be registered
    im = np.array(misc.imread(filename), dtype='float64')
    # Load reference image
    ref_im = np.array(misc.imread(ref_filename), dtype='float64')
    # Calculate shift between images
    x, y, a, b = image_registration.chi2_shift(im, ref_im)
    return (x, y)


def register_images(registration_files, reference_files, output_file):
    '''
    Calculate shift between a set of two images (image to register and
    reference image) from two different acquisition cycles
    and store the results in an HDF5 file.

    The HDF5 file will have the following internal hierarchical structure::

        /
        /cycle1                Group
        /cycle1/x_shift        Dataset {n}  : INTEGER
        /cycle1/y_shift        Dataset {n}  : INTEGER
        /cycle1/file_name      Dataset {n}  : STRING
        /cycle2                Group
        /cycle2/x_shift        Dataset {n}  : INTEGER
        /cycle2/y_shift        Dataset {n}  : INTEGER
        /cycle2/file_name      Dataset {n}  : STRING
        ...

    where `n` is the number of image sites per cycle.

    Parameters
    ----------
    registration_files: List[Dict[str, List[str]]]
        name of image files that should be registered
    reference_files: List[str]
        name of image files used as reference for registration
    output_file: str
        name of the HDF5 file, where calculated values will be stored
    '''
    out = dict()
    for cycle, files in registration_files.iteritems():
        print '.. "%s"' % cycle
        out[cycle] = dict()
        out[cycle]['x_shift'] = []
        out[cycle]['y_shift'] = []
        out[cycle]['file_name'] = []
        for site in xrange(len(files)):
            reg_filename = files[site]
            print '... registration: %s' % reg_filename
            ref_filename = reference_files[site]
            print '... reference: %s' % ref_filename

            # Calculate shift between images
            x, y = calculate_shift(reg_filename, ref_filename)

            # Store shift values and name of the registered image
            out[cycle]['x_shift'].append(int(x))
            out[cycle]['y_shift'].append(int(y))
            out[cycle]['file_name'].append(os.path.basename(reg_filename))

    print '. Store registration in file: %s' % output_file
    f = h5py.File(output_file, 'w')
    for cycle, data in out.iteritems():
        for feature, values in data.iteritems():
            # The calculated features will be stored
            # in separate datasets grouped by cycle
            hdf5_location = '%s/%s' % (cycle, feature)
            f.create_dataset(hdf5_location, data=values)
    f.close()


def calculate_local_overlap(x_shift, y_shift):
    '''
    Calculates the overlap of images at one acquisition site
    across different acquisition cycles.

    Parameters
    ----------
    x_shift: List[int]
        shift values in x direction
    y_shift: List[int]
        shift values in y direction

    Returns
    -------
    List[int]
        upper, lower, right and left overlap
    '''
    # in y direction
    y_positive = [i > 0 for i in y_shift]
    y_negetive = [i < 0 for i in y_shift]
    if any(y_positive):  # down
        bottom = []
        for i in y_positive:
            bottom.append(y_shift[i])
        bottom = max(bottom)
    else:
        bottom = 0

    if any(y_negetive):  # up
        top = []
        for i in y_negetive:
            top.append(y_shift[i])
        top = abs(min(top))
    else:
        top = 0

    # in x direction
    x_positive = [i > 0 for i in x_shift]
    x_negetive = [i < 0 for i in x_shift]
    if any(x_positive):  # right
        right = []
        for i in x_positive:
            right.append(x_shift[i])
        right = max(right)
    else:
        right = 0

    if any(x_negetive):  # left
        left = []
        for i in x_negetive:
            left.append(x_shift[i])
        left = abs(min(left))
    else:
        left = 0

    return (top, bottom, right, left)


def fuse_registration(output_files, cycle_names):
    '''
    For each acquisition cycle, fuse calculated shifts stored across
    several HDF5 files.

    Parameters
    ----------
    output_files: List[str]
        names of HDF5 files, where registration results were stored
    cycle_names: List[str]
        names of cycles (correspond to groups in HDF5 files)

    Returns
    -------
    List[Dict[str, List[str or int]]]
        "xShift", "yShift", and "fileName" of each registered image
    '''
    descriptor = list()
    for i, key in enumerate(cycle_names):
        descriptor.append(dict())
        descriptor[i]['xShift'] = []
        descriptor[i]['yShift'] = []
        descriptor[i]['fileName'] = []
    # Combine output from different output files
    for output in output_files:
        f = h5py.File(output, 'r')
        for i, key in enumerate(cycle_names):
            descriptor[i]['fileName'].extend(f[key]['file_name'][()])
            descriptor[i]['xShift'].extend(f[key]['x_shift'][()])
            descriptor[i]['yShift'].extend(f[key]['y_shift'][()])
        f.close()
    return descriptor


def calculate_overlap(descriptor, max_shift):
    '''
    Calculate the maximum overlap of images across all sites and
    across all acquisition cycles. The images will later be cropped according
    to this overlap. In order to limit the extent of cropping, `max_shift` can
    be set.

    Parameters
    ----------
    descriptor: List[Dict[str, List[str or int]]]
        calculated shift values (and names) of registered images for
        each acquisition cycle
    max_shift: int
        maximally tolerated shift (in pixels)

    Returns
    -------
    Tuple[List[int]]
        upper, lower, right, and left overlap per site (in pixels)
        and indices of sites were shift exceeds maximally tolerated value
    '''
    top_ol = []
    bottom_ol = []
    right_ol = []
    left_ol = []
    no_shift = []
    number_of_sites = len(descriptor[0]['xShift'])
    print '. number of sites: %d' % number_of_sites
    for site in xrange(number_of_sites):
        x_shift = np.array([c['xShift'][site] for c in descriptor])
        y_shift = np.array([c['yShift'][site] for c in descriptor])
        no_shift.append(any(abs(x_shift) > max_shift) or
                        any(abs(y_shift) > max_shift))
        (top, bottom, right, left) = calculate_local_overlap(x_shift, y_shift)
        top_ol.append(top)
        bottom_ol.append(bottom)
        right_ol.append(right)
        left_ol.append(left)

    # Calculate total overlap across all sites
    top_ol = int(max(map(abs, top_ol)))
    bottom_ol = int(max(map(abs, bottom_ol)))
    right_ol = int(max(map(abs, right_ol)))
    left_ol = int(max(map(abs, left_ol)))

    # Limit total overlap by maximally tolerated shift
    if top_ol > max_shift:
        top_ol = max_shift
    if bottom_ol > max_shift:
        bottom_ol = max_shift
    if right_ol > max_shift:
        right_ol = max_shift
    if left_ol > max_shift:
        left_ol = max_shift

    return (top_ol, bottom_ol, right_ol, left_ol, no_shift)


class Registration(object):

    '''
    Class for registration of images from different acquisition cycles.
    '''

    def __init__(self, cycles, reference_cycle=None, reference_channel=None):
        '''
        Initialize Registration class.

        Parameters
        ----------
        cycles: List[Subexperiment]
        reference_cycle: int
            cycle that should be used as reference for image registration
        reference_channel: int
            channel from which images should be used for registration
        '''
        self.cycles = cycles
        self.ref_cycle = reference_cycle
        self.ref_channel = reference_channel
        self.experiment_dir = os.path.dirname(self.cycles[0].directory)
        self.experiment = self.cycles[0].experiment
        self.registration_dir = os.path.join(self.experiment_dir,
                                             'registration')
        self.joblist_file = os.path.join(self.experiment_dir,
                                         'align_%s.jobs' % self.experiment)
        self._image_files = None

    @property
    def image_files(self):
        '''
        Returns
        -------
        List[List[str]]
            image files of the reference channel grouped by cycle
        '''
        if self._image_files is None:
            image_filenames = []
            if not self.ref_channel:
                raise IOError('Parameter "reference_channel" is required '
                              'to list image files')
            for c in self.cycles:
                # extract files of reference channel
                files = [f.filename for f in c.project.image_files
                         if f.channel == self.ref_channel]
                files = natsort.natsorted(files)  # ensure correct order
                image_filenames.append(files)
            self._image_files = image_filenames
        return self._image_files

    def create_output_dir(self):
        '''
        Create "registration" folder that will hold the HDF5 files,
        where the calculated shift values will be stored.
        There will be one HDF5 file per job (i.e. batch).
        '''
        if not os.path.exists(self.registration_dir):
            os.mkdir(self.registration_dir)

    def create_joblist(self, batch_size):
        '''
        Create list of jobs for parallel processing.

        A joblist has the following structure (YAML)::

            - job_id: int
              registration_files: Dict[str, List[str]]
              reference_files:  List[str]
              output_file: str

            - job_id: int
              registration_files: Dict[str, List[str]]
              reference_files:  List[str]
              output_file: str

            ...

        Parameters
        ----------
        batch_size: int
            number of batches

        Returns
        -------
        List[Dict[str, List[str] or str]]
            job description

        Raises
        ------
        IOError
            when argument `reference_cycle` is not specified
        '''
        if not self.ref_cycle:
            raise IOError('Parameter "reference_cycle" is required '
                          'for joblist creation')

        joblist = list()
        ref_files = tmt.cluster.create_batches(self.image_files[self.ref_cycle],
                                               batch_size)
        n_batches = len(ref_files)
        # Create a list of dictionaries holding the image filenames per batch
        # segregated for the different cycles
        n_cycles = len(self.image_files)
        reg_files = [dict() for x in xrange(n_batches)]
        for x in xrange(n_cycles):
            batches = tmt.cluster.create_batches(self.image_files[x],
                                                 batch_size)
            for i, batch in enumerate(batches):
                reg_files[i][self.cycles[x].name] = batch

        for i in xrange(n_batches):
            output_filename = os.path.join(self.registration_dir,
                                           'align_%.5d.output' % i)
            joblist.append({
                'job_id': i+1,                       # int
                'registration_files': reg_files[i],  # Dict[List[str]]
                'reference_files': ref_files[i],     # List[str]
                'output_file': output_filename       # str
            })
        self.joblist = joblist
        return joblist

    def write_joblist(self):
        '''
        Write joblist to file as YAML.
        '''
        tmt.cluster.write_joblist(self.joblist_file, self.joblist)

    def read_joblist(self):
        '''
        Read joblist from YAML file.

        Returns
        -------
        List[dict[str, list[str] or str]]
            job description
        '''
        return tmt.cluster.read_joblist(self.joblist_file)
