import re
import os
import yaml
from natsort import natsorted
from tmt.image import is_image_file
from tmt.illumstats import Illumstats
from tmt.image import ChannelImage, SegmentationImage
from tmt.shift import ShiftDescriptor


class Project(object):
    '''
    Utility class for a project.

    A project represents the directory that holds the image folder
    and potentially additional folders for segmentation, shift, and
    illumination statistics files.
    The project folder may either correspond to an "experiment" or a
    "subexperiment".

    See also
    --------
    `experiment.Experiment`_
    `experiment.Subexperiment`_
    '''

    def __init__(self, project_dir, cfg):
        '''
        Initialize an instance of class Project.

        Parameters
        ----------
        project_dir: str
            absolute path to project folder
        cfg: Dict[str, str]
            configuration settings

        Raises
        ------
        IOError
            when `project_dir` is not a directory
        '''
        self.project_dir = project_dir
        if not os.path.isdir(project_dir):
            raise IOError('Failed to initialize class "Project" because '
                          '"%s" is not a directory.'
                          % self.project_dir)
        self.cfg = cfg
        self._experiment_dir = None
        self._experiment = None
        self._subexperiment = None
        self.is_MPcycle = False
        self._image_dir = None
        self._image_files = None
        self._image_info = None
        self._segmentation_dir = None
        self._segmentation_files = None
        self._segmentation_info = None
        self._shift_dir = None
        self._shift_file = None
        self._stats_dir = None
        self._stats_files = None

    @property
    def experiment_dir(self):
        '''
        Returns
        -------
        str
            path to experiment directory, determined from `project_dir`

        Raises
        ------
        OSError
            when determined directory does not exist
        '''
        if self._experiment_dir is None:
            if self.cfg['SUBEXPERIMENTS_EXIST']:
                levels = 1
            else:
                levels = 0
            exp_dir = os.path.realpath(os.path.join(self.project_dir,
                                                    * ['..'] * levels))
            if not os.path.exists(exp_dir):
                raise OSError('Experiment directory could not be determined '
                              'correctly. The determined directory does not '
                              'exist: %s' % exp_dir)
            self._experiment_dir = exp_dir
        return self._experiment_dir

    @property
    def experiment(self):
        '''
        Returns
        -------
        str
            name of the experiment
        '''
        return os.path.basename(self.experiment_dir)

    @property
    def subexperiment(self):
        '''
        Returns
        -------
        str
            name of the subexperiment
            (empty string if the project is not a subexperiment)
        '''
        if self._subexperiment is None:
            if self.cfg['SUBEXPERIMENTS_EXIST']:
                self._subexperiment = os.path.basename(self.project_dir)
            else:
                self._subexperiment = ''
        return self._subexperiment

    @property
    def image_dir(self):
        '''
        Returns
        -------
        str
            path to directory holding image files
        '''
        if self._image_dir is None:
            folder = self.cfg['IMAGE_FOLDER_FORMAT'].format(
                            experiment_dir=self.experiment_dir,
                            subexperiment=self.subexperiment,
                            sep=os.path.sep)
            self._image_dir = folder
        return self._image_dir

    @property
    def image_files(self):
        '''
        Returns
        -------
        List[tmt.image.ChannelImage]
            image files (intensity images)

        Raises
        ------
        OSError
            when image directory does not exist
        IOError
            when no image files are found
        '''
        if self._image_files is None:
            if not os.path.exists(self.image_dir):
                raise OSError('Image directory does not exist: %s'
                              % self.image_dir)
            files = [os.path.join(self.image_dir, f)
                     for f in os.listdir(self.image_dir) if is_image_file(f)]
            files = natsorted(files)
            if not files:
                raise IOError('No image files found in "%s"' % self.image_dir)
            self._image_files = [ChannelImage(f, self.cfg, self.image_info)
                                 for f in files]
        return self._image_files

    @property
    def image_info(self):
        '''
        Returns
        -------
        Dict[str, Dict[str, int]]
            information about image files, such as "site", "row", "column",
            and "channel" number
        '''
        if (not self.cfg['INFO_FROM_FILENAME']
                and self._image_info is None):
            info_file = os.path.join(self.segmentation_dir,
                                     self.cfg['IMAGE_INFO_FILE_FORMAT'])
            self._image_info = yaml.load(open(info_file))
        return self._image_info

    @property
    def segmentation_dir(self):
        '''
        Returns
        -------
        str
            path to directory holding segmentation image files
        '''
        if self._segmentation_dir is None:
            try:
                # In case of MPCycle experiments the segmentation directory
                # is defined in the JSON shift descriptor file. The path
                # is stored for use in Jterator pipelines. Therefore, we
                # have to remove all relative parts of the path.
                folder = os.path.join(
                            self.project_dir,
                            re.sub(r'../', '',
                                   self.shift_file.description.segmentationDir))
            except:
                folder = self.cfg['SEGMENTATION_FOLDER_FORMAT'].format(
                                    experiment_dir=self.experiment_dir,
                                    subexperiment=self.subexperiment,
                                    sep=os.path.sep)
            self._segmentation_dir = folder
        return self._segmentation_dir

    @property
    def segmentation_files(self):
        '''
        Returns
        -------
        List[tmt.image.SegmentationImage]
            segmentation image files (mask images)

        Raises
        ------
        OSError
            when segmentation directory does not exist
        IOError
            when no segmentation files are found
        '''
        if self._segmentation_files is None:
            if not os.path.exists(self.segmentation_dir):
                raise OSError('Segmentation directory does not exist: %s'
                              % self.segmentation_dir)
            files = [os.path.join(self.segmentation_dir, f)
                     for f in os.listdir(self.segmentation_dir)
                     if is_image_file(f)]
            files = natsorted(files)
            if not files:
                raise IOError('No segmentation files found in "%s"'
                              % self.segmentation_dir)
            self._segmentation_files = \
                [SegmentationImage(f, self.cfg, self.segmentation_info)
                 for f in files]
        return self._segmentation_files

    @property
    def segmentation_info(self):
        '''
        Returns
        -------
        Dict[str, Dict[str, int]]
            information about segmentation files, such as "site", "row",
            "column" number and "objects" name
        '''
        if (not self.cfg['INFO_FROM_FILENAME']
                and self._segmentation_info is None):
            info_file = os.path.join(self.segmentation_dir,
                                     self.cfg['SEGMENTATION_INFO_FILE_FORMAT'])
            self._segmentation_info = yaml.load(open(info_file))
        return self._segmentation_info

    @property
    def stats_dir(self):
        '''
        Returns
        -------
        str
            path to directory holding illumination statistic files
        '''
        if self._stats_dir is None:
            folder = self.cfg['STATS_FOLDER_FORMAT'].format(
                                experiment_dir=self.experiment_dir,
                                subexperiment=self.subexperiment,
                                sep=os.path.sep)
            self._stats_dir = folder
        return self._stats_dir

    @property
    def stats_files(self):
        '''
        Returns
        -------
        List[tmt.illumstats.Illumstats]
            files containing calculated illumination statistics

        Raises
        ------
        OSError
            when stats directory does not exist
        IOError
            when no illumination statistic files are found
        '''
        if self._stats_files is None:
            stats_pattern = self.cfg['STATS_FILE_FORMAT'].format(channel='\d+')
            stats_pattern = re.compile(stats_pattern)
            if not os.path.exists(self.stats_dir):
                raise OSError('Stats directory does not exist: %s'
                              % self.stats_dir)
            files = [os.path.join(self.stats_dir, f)
                     for f in os.listdir(self.stats_dir)
                     if re.search(stats_pattern, f)]
            files = natsorted(files)
            if not files:
                raise IOError('No illumination statistic files found in "%s"'
                              % self.stats_dir)
            self._stats_files = [Illumstats(f, self.cfg) for f in files]
        return self._stats_files

    @property
    def shift_dir(self):
        '''
        Returns
        -------
        str
            path to directory holding shift descriptor files
        '''
        if self._shift_dir is None:
            folder = self.cfg['SHIFT_FOLDER_FORMAT'].format(
                                experiment_dir=self.experiment_dir,
                                subexperiment=self.subexperiment,
                                sep=os.path.sep)
            self._shift_dir = folder
        return self._shift_dir

    @property
    def shift_file(self):
        '''
        Returns
        -------
        Namespacified
            description (content of a shift descriptor JSON file)
            and filename

        Raises
        ------
        OSError
            when shift directory does not exist
        IOError
            when no shift descriptor file is found
        '''
        if self._shift_file is None:
            shift_pattern = self.cfg['SHIFT_FILE_FORMAT']
            shift_pattern = re.compile(shift_pattern)
            if not os.path.exists(self.shift_dir):
                raise OSError('Shift directory does not exist: %s'
                              % self.shift_dir)
            files = [os.path.join(self.shift_dir, f)
                     for f in os.listdir(self.shift_dir)
                     if re.search(shift_pattern, f)]
            # there should only be one file, but in case there are more take
            # the first one
            files = natsorted(files)
            if not files:
                raise IOError('No shift descriptor file found in "%s" '
                              'that matches the provided pattern "%s".\n'
                              'Check your configuration settings!'
                              % (self.shift_dir,
                                 self.cfg['SHIFT_FILE_FORMAT']))
            self._shift_file = ShiftDescriptor(files[0], self.cfg)
        return self._shift_file
