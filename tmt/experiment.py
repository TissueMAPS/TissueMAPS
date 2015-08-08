import re
import os
from natsort import natsorted
from utils import regex_from_format_string
from image import is_image_file
from plates import WellPlate
from plates import Slide
from reader import read_yaml
from metadata import SegmentationMetadata


class Experiment(object):
    '''
    Class for an experiment.

    An experiment represents a folder on disk that contains image files
    and additional data associated with the images, such as metainformation,
    measured features, segmentations, etc. The structure of the directory tree
    and the location of files is defined via format strings
    in the configuration settings file.

    An experiment consists of one or more cycles. A cycle represents a
    particular time point of image acquisition for a given sample.
    In the simplest case, the experiment represents a cycle itself, i.e. a
    single round of image acquisition. However, the experiment may also
    represent a time series, consisting of several iterative rounds of
    image acquisitions. In this case there are multiple cycles and each cycle
    should be represented by a separate subfolder on disk. The names of these
    subexperiment folders should encode the name of the experiment as well as
    the cycle number, i.e. the one-based index of the time series sequence.
    For example, given an experiment called "myExperiment",
    the directory tree could be structured as follows::

        myExperiment           # experiment folder
            myExperiment_1     # subexperiment folder corresponding to cycle #1
            myExperiment_2     # subexperiment folder corresponding to cycle #2
            ...

    The exact format of cycle folders can be specified with the key
    *CYCLE_FOLDER_FORMAT* in the configuration settings file.

    See also
    --------
    `subexperiments.Cycle`_
    `tmt.conifg`_
    '''

    def __init__(self, experiment_dir, cfg):
        '''
        Initialize an instance of class Experiment.

        Parameters
        ----------
        experiment_dir: str
            absolute path to experiment folder
        cfg: Dict[str, str]
            configuration settings

        See also
        --------
        `tmt.config`_
        '''
        self.cfg = cfg
        self.experiment_dir = os.path.abspath(experiment_dir)
        self._segmentation_files = None
        self._segmentations = None

    @property
    def name(self):
        '''
        Returns
        -------
        str
            name of the experiment
        '''
        self._name = os.path.basename(self.experiment_dir)
        return self._name

    def _is_valid_cycle(self, folder):
        '''
        Determine whether a folder represents a valid "cycle".

        The format of a cycle folders is defined in the configuration settings.
        The format string is converted to a regular expression. If the regular
        expression matches the folder name, the folder represents a cycle.

        Returns
        -------
        bool
        '''
        regexp = regex_from_format_string(
                    self.cfg['CYCLE_FOLDER_FORMAT'])
        return(re.match(regexp, folder)
               and os.path.isdir(os.path.join(self.experiment_dir, folder)))

    @property
    def cycles(self):
        '''
        An experiment folder may contain several cycles or represent a cycle
        itself. Depending on the *plate format*, a cycle corresponds either to
        a well plate or a slide. This is defined by the key *WELLPLATE_FORMAT*
        in the configuration settings file.

        Returns
        -------
        List[WellPlate or Slide]
            object representations of cycles

        See also
        --------
        `plates.WellPlate`_
        `plates.Slide`_
        `tmt.config`_
        '''
        if self._subexperiments is None:
            subexperiment_folders = os.listdir(self.experiment_dir)
            # sort subexperiment folders
            subexperiment_folders = natsorted(subexperiment_folders)
            cycle_dirs = [os.path.join(self.experiment_folder, f)
                          for f in subexperiment_folders
                          if self._is_valid_cycle(f)]
            if not cycle_dirs:
                # in this case, the cycle directory is the same as the
                # the experiment directory
                cycle_dirs = self.experiment_dir
            if self.cfg['WELLPLATE_FORMAT']:
                n_wells = self.cfg['NUMBER_OF_WELLS']
                cycles = [WellPlate(c, self.cfg, n_wells) for c in cycle_dirs]
            else:
                cycles = [Slide(c, self.cfg) for c in cycle_dirs]
            self._cycles = cycles
        return self._cycles

    @property
    def n_cycles(self):
        '''
        Returns
        -------
        int
            number of cycles in the experiment
        '''
        self._n_cycles = len(self.cycles)
        return self._n_cycles

    @property
    def data_file(self):
        '''
        Measurement data for all cycles are stored in a single HDF5 file.
        The format of the filename is defined by the key *DATA_FILE_FORMAT*
        in the configuration settings file.

        Returns
        -------
        str
            absolute path to the HDF5 file holding the complete dataset
        
        See also
        --------
        `dafu`_
        '''
        self._data_filename = self.cfg['DATA_FILE_FORMAT'].format(
                                            experiment_dir=self.experiment_dir,
                                            sep=os.path.sep)
        return self._data_filename

    @property
    def layers_dir(self):
        '''
        Image pyramids for all cycles are stored in single folder.
        The format of the folder name is defined by the key
        *LAYERS_FOLDER_FORMAT* in the configuration settings file.

        Returns
        -------
        str
            absolute path to the folder holding the layers (zoomify pyramids)
        '''
        self._layers_dir = self.cfg['LAYERS_FOLDER_FORMAT'].format(
                                            experiment_dir=self.experiment_dir,
                                            sep=os.path.sep)
        return self._layers_dir
