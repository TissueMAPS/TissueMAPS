import re
import os
import json
from natsort import natsorted
from os.path import join, basename, isdir
from tmt.image import is_image_file
from tmt.illumstats import Illumstats
from tmt.image import IntensityImage, MaskImage


class Project(object):
    '''
    Utility class for a project.
    
    A project represents the directory that holds the image folder
    and potentially additional folders for segmentation, shift, and
    illumination statistics files.
    The project folder may either correspond to an "experiment"
    or a "subexperiment".
    '''

    def __init__(self, experiment_dir, cfg, subexperiment=''):
        '''
        Initiate Project class.

        Parameters
        ----------
        experiment_dir: str
                        absolute path to experiment folder
        cfg: Dict[str, str]
             configuration settings
        subexperiment_name: str
                            name of subexperiment folder (empty by default)
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
    # to use these names to create the folders!

    @property
    def image_dir(self):
        '''
        Returns
        -------
        str
        path to directory holding image files
        '''
        if not self._image_dir:
            folder = self.cfg['IMAGE_FOLDER_LOCATION'].format(
                            experiment_dir=self.experiment_dir,
                            subexperiment=self.subexperiment)
            self._image_dir = folder
        return self._image_dir

    @property
    def image_files(self):  # def get_image_files(self):
        '''
        Returns
        -------
        List[IntensityImage]
        '''
        if not self._image_files:
            files = [join(self.image_dir, f)
                     for f in os.listdir(self.image_dir) if is_image_file(f)]
            files = natsorted(files)
            if not files:
                raise Exception('No image files found in "%s"'
                                % self.image_dir)
            self._image_files = [IntensityImage(f, self.cfg) for f in files]
        return self._image_files

    @property
    def segmentation_dir(self):
        '''
        Returns
        -------
        str
        path to directory holding segmentation files
        '''
        if not self._segmentation_dir:
            try:
                # In case of MPCycle experiments the segmentation directory
                # is defined in the JSON shift descriptor file. The path
                # is stored for use in Jterator pipelines. Therefore, we
                # have to remove all relative parts of the path.
                folder = join(self.experiment_dir,
                              re.sub(r'../', '',
                                     self.shift_file['segmentationDirectory']))
            except:
                folder = self.cfg['SEGMENTATION_FOLDER_LOCATION'].format(
                                    experiment_dir=self.experiment_dir,
                                    subexperiment=self.subexperiment)
            self._segmentation_dir = folder
        return self._segmentation_dir

    @property
    def segmentation_files(self):
        '''
        Returns
        -------
        List[MaskImage]
        '''
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
        '''
        Returns
        -------
        str
        path to directory holding illumination statistic files
        '''
        if not self._stats_dir:
            folder = self.cfg['STATS_FOLDER_LOCATION'].format(
                                experiment_dir=self.experiment_dir,
                                subexperiment=self.subexperiment)
            self._stats_dir = folder
        return self._stats_dir

    @property
    def stats_files(self):
        '''
        Returns
        -------
        List[Illumstats]
        '''
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
        '''
        Returns
        -------
        str
        path to directory holding shift descriptor files
        '''
        if not self._shift_dir:
            folder = self.cfg['SHIFT_FOLDER_LOCATION'].format(
                                experiment_dir=self.experiment_dir,
                                subexperiment=self.subexperiment)
            self._shift_dir = folder
        return self._shift_dir

    @property
    def shift_file(self):
        '''
        Returns
        -------
        dict
        content of a shift descriptor JSON file
        '''
        if not self._shift_file:
            shift_pattern = self.cfg['SHIFT_FILE_FORMAT']
            shift_pattern = re.compile(shift_pattern)
            files = [join(self.shift_dir, f)
                     for f in os.listdir(self.shift_dir)
                     if re.search(shift_pattern, f)]
            # there should only be one file, but in case there are more take
            # the first one
            files = natsorted(files)
            if not files:
                raise Exception('No shift descriptor file found in "%s"'
                                % self.shift_dir)
            self._shift_file = json.load(open(files[0]))
        return self._shift_file
