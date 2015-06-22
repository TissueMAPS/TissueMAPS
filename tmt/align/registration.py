import os
import yaml
import natsort
import h5py
import numpy as np
from scipy import misc
import image_registration


def calculate_shift(filename, ref_filename):
    '''
    Calculate shift between two images from different cycles.

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

    "Apparently astronomical images look a lot like microscopic images." [*]

    [*] http://image-registration.readthedocs.org/en/latest/
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
    Calculate the shift between a set of images (image to register and
    reference image) and store the results in an HDF5 file.

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
        print '. Process "%s"' % cycle
        out[cycle] = dict()
        out[cycle]['x_shift'] = []
        out[cycle]['y_shift'] = []
        out[cycle]['reg_file'] = []
        for site in xrange(len(files)):
            print '.. Process site #%d' % (site+1)
            reg_filename = files[site]
            print '... registration: %s' % reg_filename
            ref_filename = reference_files[site]
            print '... reference: %s' % ref_filename

            # Calculate shift between images
            x, y = calculate_shift(reg_filename, ref_filename)

            # Store shift values and name of the registered image
            out[cycle]['x_shift'].append(int(x))
            out[cycle]['y_shift'].append(int(y))
            out[cycle]['reg_file'].append(os.path.basename(reg_filename))

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
                  name of HDF5 files, where registration results were stored
    cycle_names: List[str]
                 name of cycles (correspond to groups in HDF5 files)

    Returns
    -------
    List[Dict[str, List[str or int]]]
    "xShift", "yShift", and "fileName" of each registered image
    '''
    descriptor = list()
    for i, key in enumerate(cycle_names):
        descriptor[i] = dict()
        descriptor[i]['xShift'] = []
        descriptor[i]['yShift'] = []
        descriptor[i]['fileName'] = []
    # Combine output from different output files
    for output in output_files:
        f = h5py.File(output, 'r')
        for i, key in enumerate(cycle_names):
            descriptor[i]['fileName'].extend(f[key]['reg_file'][()])
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
               maximally tolerated shift value

    Returns
    -------
    Tuple[List[int]]
    upper, lower, right, and left overlap per site
    and indices of sites were shift exceeds maximally tolerated value
    '''
    top = []
    bottom = []
    right = []
    left = []
    no_shift = []
    number_of_sites = len(descriptor[0]['xShift'])
    print '. number of sites: %d' % number_of_sites
    for site in xrange(number_of_sites):
        x_shift = [c['xShift'][site] for c in descriptor.values()]
        y_shift = [c['yShift'][site] for c in descriptor.values()]
        no_shift.append(abs(x_shift) > max_shift or abs(y_shift) > max_shift)
        (top, bottom, right, left) = calculate_local_overlap(x_shift, y_shift)
        top.append(top)
        bottom.append(bottom)
        right.append(right)
        left.append(left)

    # Calculate total overlap across all sites
    top = int(max(map(abs, top)))
    bottom = int(max(map(abs, bottom)))
    right = int(max(map(abs, right)))
    left = int(max(map(abs, left)))

    # Limit total overlap by maximally tolerated shift
    if top > max_shift:
        top = max_shift
    if bottom > max_shift:
        bottom = max_shift
    if right > max_shift:
        right = max_shift
    if left > max_shift:
        left = max_shift

    return (top, bottom, right, left, no_shift)


class Registration(object):

    '''
    Class for registration of images from different acquisition cycles.
    '''

    def __init__(self, cycles, reference_cycle=None, reference_channel=None):
        '''
        Initiate Registration class.

        Parameters
        ----------
        cycles: List[Subexperiment]
        reference_cycle: int
                         cycle that should be used as reference for
                         image registration
        reference_channel: int
                           channel from which images should be used for
                           registration
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
        For each cycle list image files of the reference channel.

        Returns
        -------
        List[List[str]]
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

        A joblist has the following structure (YAML):

            - registration_files: Dict[str, List[str]]
              reference_files:  List[str]
              output_file: str

            - registration_files: Dict[str, List[str]]
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
        '''
        def create_batches(l, n):
            '''
            Separate a list into several n-sized sub-lists.

            Parameters
            ----------
            l: list
            n: int

            Returns
            -------
            List[list]
            '''
            n = max(1, n)
            return [l[i:i + n] for i in range(0, len(l), n)]

        if not self.ref_cycle:
            raise IOError('Parameter "reference_cycle" is required '
                          'for joblist creation')

        joblist = list()
        ref_filenames = create_batches(self.image_files[self.ref_cycle],
                                       batch_size)
        n_batches = len(ref_filenames)
        # Create a list of dictionaries holding the image filenames per batch
        # segregated for the different cycles
        n_cycles = len(self.image_files)
        reg_filenames = [dict() for x in xrange(n_batches)]
        for x in xrange(n_cycles):
            batches = create_batches(self.image_files[x], batch_size)
            for i, batch in enumerate(batches):
                reg_filenames[i]['cycle%d' % (x+1)] = batch

        for i in xrange(n_batches):
            output_filename = os.path.join(self.registration_dir,
                                           'align_%.5d.output' % i)
            joblist.append({
                'registration_files': reg_filenames[i],  # Dict[List[str]]
                'reference_files': ref_filenames[i],     # List[str]
                'output_file': output_filename           # str
            })
        self.joblist = joblist
        return joblist

    def write_joblist(self):
        '''
        Write joblist to file as YAML.
        '''
        with open(self.joblist_file, 'w') as outfile:
            outfile.write(yaml.dump(self.joblist, default_flow_style=False))

    def read_joblist(self):
        '''
        Read joblist from YAML file.

        Returns
        -------
        List[dict[str, list[str] or str]]
        '''
        with open(self.joblist_file, 'r') as joblist_file:
            return yaml.load(joblist_file.read())

