import glob
import os
import re
import tmt.cluster
from tmt.visi.stk2png import Stk2png


class Stk(object):
    '''
    Class for a visi project.

    A visi project corresponds to a folder holding .stk and .nd files.
    '''

    def __init__(self, input_dir, wildcards, config):
        '''
        Initialize Stk class.

        Parameters
        ----------
        input_dir: str
            path to the directory holding the .stk files
        wildcards: str
            globbing pattern to select subset of .stk files
        config: Dict[str, str]
            configuration settings
        '''
        self.input_dir = input_dir
        self.wildcards = wildcards
        self.cfg = config
        self.experiment_dir = os.path.dirname(input_dir)
        self.experiment = os.path.basename(self.experiment_dir)
        self.joblist_file = os.path.join(self.experiment_dir,
                                         'visi_%s.jobs' % self.experiment)
        self._files = None
        self._nd_files = None
        self._stk_files = None
        self._output_dirs = None

    @property
    def files(self):
        '''
        Select files from input directory that match globbing pattern.

        Returns
        -------
        List[str]
        '''
        if self._files is None:
            self._files = glob.glob(os.path.join(self.input_dir,
                                                 self.wildcards))
            if not self._files:
                raise ValueError('No files found in directory "%s" that '
                                 'match pattern "%s"'
                                 % (self.input, self.wildcards))
        return self._files

    @property
    def nd_files(self):
        '''
        Extract .nd files from the list of selected files.

        Returns
        -------
        List[str]
        '''
        if self._nd_files is None:
            r = re.compile('.*\.nd$')
            nd_files = filter(r.search, self.files)
            if not nd_files:
                raise ValueError('No .nd files found in file list.')
            self._nd_files = nd_files
        return self._nd_files

    @property
    def stk_files(self):
        '''
        Extract .stk files from the list of selected files,
        grouped per .nd file.

        Returns
        -------
        List[List[str]]
        '''
        if self._stk_files is None:
            stk_files = [list() for x in self.nd_files]
            for i, nd in enumerate(self.nd_files):
                nd_base = os.path.splitext(os.path.basename(nd))[0]
                r = re.compile(r'%s_.*stk$' % nd_base)
                stk_files[i] = filter(r.search, self.files)
            if not stk_files[i]:
                raise ValueError('No .stk files found in list of files')
            self._stk_files = stk_files
        return self._stk_files

    def create_output_dirs(self, split_output):
        '''
        Create an output directory for each .nd file.

        There may be one or more unique output directories,
        depending on the value of the `split_output` parameter.

        Parameters
        ----------
        split_output: bool
            Should output be split into separate folders for each .nd file?

        Returns
        -------
        List[str]

        '''
        image_folder_name = self.cfg['IMAGE_FOLDER_LOCATION'].format(
                                        experiment_dir=self.experiment_dir,
                                        subexperiment='irrelevant',
                                        sep=os.path.sep)
        output_folder_name = os.path.basename(image_folder_name)
        if not output_folder_name:
            raise IOError('Output image folder name could not be '
                          'determined from configuration settings!')
        if split_output:
            nd_bases = [os.path.splitext(os.path.basename(nd))[0]
                        for nd in self.nd_files]
            # Put files corresponding to each .nd file in separate folders
            r = re.compile(r'(?P<experiment>.*)_(?P<cycle>\d+)$')
            sub_parts = map(r.search, nd_bases)
            output_sub_dirs = ['%s_%.2d' % (s.group('experiment'),
                                            int(s.group('cycle')))
                               for s in sub_parts]
        else:
            output_sub_dirs = ['' for x in xrange(len(self.nd_files))]

        # Relative path to output directories for images
        output_dirs = [os.path.join(out, output_folder_name)
                       for out in output_sub_dirs]

        for out_dir in output_dirs:
            # Build full path to output directory
            out_dir = os.path.join(self.input_dir, '..', out_dir)
            if not os.path.exists(out_dir):
                os.makedirs(out_dir)

        self.image_output_dirs = output_dirs

    def create_joblist(self, batch_size, rename=True):
        '''
        Create list of jobs for parallel processing.

        A joblist has the following structure (YAML format)::

            - job_id: int
              stk_files: List[str]
              nd_file:  str
              png_files: List[str]
              output_dir: str

            - job_id: int
              stk_files: List[str]
              nd_file:  str
              png_files: List[str]
              output_dir: str

            ...

        The `nd_file` and `stk_files` are provided as absolute path,
        while `png_files` are relative paths (relative to `output_dir`).

        Parameters
        ----------
        batch_size: int
            number of batches
        rename: bool, optional
            whether files should be renamed according to configuration settings
            (defaults to True)

        Returns
        -------
        List[dict[str, list[str] or str]]
            joblist
        '''
        joblist = list()
        count = 0
        for i, nd_file in enumerate(self.nd_files):
            batches = tmt.cluster.create_batches(self.stk_files[i], batch_size)
            for j, batch_stk_files in enumerate(batches):
                renaming = Stk2png(batch_stk_files, nd_file, self.cfg)
                renaming.format_filenames(rename)
                # Build path to output files relative to the output directory
                batch_png_files = [os.path.join(self.image_output_dirs[i], f)
                                   for f in renaming.output_files]
                count += 1
                joblist.append({
                    'job_id': count,
                    'stk_files': batch_stk_files,
                    'nd_file': nd_file,
                    'png_files': batch_png_files,
                    'output_dir': self.experiment_dir
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
        '''
        return tmt.cluster.read_joblist(self.joblist_file)
