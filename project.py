import re
import os
from natsort import natsorted
from os.path import join, basename, isdir, exists
from image_toolbox.image import is_image_file
from image_toolbox.illumstats import Illumstats
from image_toolbox.image import IntensityImage, MaskImage


class Project(object):
    '''Utility class for a project.
    A project represents the directory that holds the image folder
    and potentially additional folders for segmentation, shift, and
    illumination statistics files.
    The project folder may either correspond to the "experiment"
    or "subexperiment" directory, depending on the experiment layout.
    '''

    def __init__(self, experiment_dir, cfg, subexperiment=''):
        '''
        Initialize Project class.

        Parameters:
        :experiment_dir:        Absolute path to experiment folder : str.
        :cfg:                   Configuration settings : dict.
        :subexperiment_name:    Name of subexperiment folder : str.
        '''
        self.experiment_dir = experiment_dir
        if not isdir(experiment_dir):
            raise Exception('Failed to initialize class "Project" because '
                            '"%s" is not a directory.'
                            % self.experiment_dir)
        self.experiment = basename(experiment_dir)
        self.cfg = cfg
        self.subexperiment = subexperiment
        self.is_MPcycle = False
        self._image_dir = None
        self._image_files = None
        self._segmentation_dir = None
        self._segmentation_files = None
        self._shift_dir = None
        self._shift_file = None
        self._stats_dir = None
        self._stats_files = None

    # NOTE: We don't check whether directories exist, because this allows us
    # to use these names to create these folders!

    @property
    def image_dir(self):
        if not self._image_dir:
            folder = self.cfg['IMAGE_FOLDER_LOCATION'].format(
                            experiment_dir=self.experiment_dir,
                            subexperiment=self.subexperiment)
            self._image_dir = folder
        return self._image_dir

    @property
    def image_files(self):  # def get_image_files(self):
        # of class "IntensityImage"
        if not self._image_files:
            files = [join(self.image_dir, f)
                     for f in os.listdir(self.image_dir) if is_image_file(f)]
            files = natsorted(files)
            if not files:
                raise Exception('No image files found in "%s"'
                                % self.image_dir)
            self._image_files = [IntensityImage(f, self.cfg) for f in files]
        return self.image_files

    @property
    def segmentation_dir(self):  # def get_segmentation_dir(self):
        if not self._segmentation_dir:
            try:
                # in case of MPCycle experiments the segmentation directory
                # is defined in the JSON shift descriptor file
                folder = join(self.experiment_dir,
                              self.shift_file['SegmentationDirectory'])
            except:
                folder = self.cfg['SEGMENTATION_FOLDER_LOCATION'].format(
                                    experiment_dir=self.experiment_dir,
                                    subexperiment=self.subexperiment)
            self._segmentation_dir = folder
        return self._segmentation_dir

    @property
    def segmentation_files(self):  # def get_segmentation_files(self):
        # of class "MaskImage"
        if not self._segmentation_files:
            files = [join(self.segmentation_dir, f)
                     for f in os.listdir(self.segmentation_dir)
                     if is_image_file(f)]
            files = natsorted(files)
            if not files:
                raise Exception('No image files found in "%s"'
                                % self.segmentation_dir)
            self._segmentation_files = [MaskImage(f, self.cfg) for f in files]
        return self._segmentation_files

    @property
    def stats_dir(self):
        if not self._stats_dir:
            folder = self.cfg['STATS_FOLDER_LOCATION'].format(
                                experiment_dir=self.experiment_dir,
                                subexperiment=self.subexperiment)
            self._stats_dir = folder
        return self._stats_dir

    @property
    def stats_files(self):
        # of class "Illumstats"
        if not self._stats_files:
            stats_pattern = self.cfg['STATS_FILE_FORMAT'].format(channel='\d+')
            stats_pattern = re.compile(stats_pattern)
            files = [join(self.stats_dir, f)
                     for f in os.listdir(self.stats_dir)
                     if re.search(stats_pattern, f)]
            files = natsorted(files)
            if not files:
                raise Exception('No illumination statistic files found in "%s"'
                                % self.stats_dir)
            self._stats_files = [Illumstats(f, self.cfg) for f in files]
        return self._stats_files

    @property
    def shift_dir(self):
        if not self._shift_dir:
            folder = self.cfg['SHIFT_FOLDER_LOCATION'].format(
                                experiment_dir=self.experiment_dir,
                                subexperiment=self.subexperiment)
            self._shift_dir = folder
        return self._shift_dir

    @property
    def shift_file(self):
        if not self._shift_file:
            shift_pattern = self.cfg['SHIFT_FILE_FORMAT']
            shift_pattern = re.compile(shift_pattern)
            files = [join(self.shift_dir, f)
                     for f in os.listdir(self.shift_dir)
                     if re.search(shift_pattern, f)]
            # there should only be one file, but in case there are more take
            # the first one
            files = natsorted(files)[0]
            if not files:
                raise Exception('No shift descriptor file found in "%s"'
                                % self.shift_dir)
            self._shift_file = files
        return self._shift_file
