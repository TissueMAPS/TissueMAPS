import glob
import os
import re
import tmt


class Stk(object):
    '''
    Class for a visi project.

    A visi project corresponds to a folder holding .stk and .nd files.
    '''

    def __init__(self, input_dir, wildcards):
        self.input_dir = input_dir
        self.wildcards = wildcards
        self.experiment_dir = os.path.dirname(input_dir)
        self.experiment = os.path.basename(self.experiment_dir)
        self.joblist_file = os.path.join(self.experiment_dir,
                                         'visi_%s.joblist' % self.experiment)
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
        Extract .stk files from the list of selected files, grouped by .nd file.

        Returns
        -------
        List[list]
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

    def create_output_dirs(self, output_folder_name, split_output):
        '''
        Create an output directory for each .nd file.

        The elements may be the same or different depending on the value
        of `split_output`.

        Parameters
        ----------

        output_folder_name: str
                            Name of the output folder.

        split_output: bool
                      Should output be split into separate folders for each
                      .nd file?

        Returns
        -------

        List[str]

        '''
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

        # Build full path to output directory
        output_dirs = [os.path.join(self.input_dir, '..',
                                    out, output_folder_name)
                       for out in output_sub_dirs]

        for out_dir in output_dirs:
            if not os.path.exists(out_dir):
                os.makedirs(out_dir)

        self.output_dirs = output_dirs

    def create_joblist(self, batch_size):
        '''
        Create list of jobs for parallel processing.

        A joblist has the following structure:

            - job_id: int
              stk_files: List[str]
              nd_file:  str
              output_dir: str

            - job_id: int
              stk_files: List[str]
              nd_file:  str
              output_dir: str

            ...

        Parameters
        ----------
        batch_size: int
                    number of batches

        Returns
        -------
        List[dict[str, list[str] or str]]
        '''
        joblist = list()
        for i, nd in enumerate(self.nd_files):
            batches = tmt.cluster.create_batches(self.stk_files[i], batch_size)
            for j, batch in enumerate(batches):
                joblist.append({
                    'job_id': i*len(batches)+j+1,
                    'stk_files': batch,
                    'nd_file': nd,
                    'output_dir': self.output_dirs[i]
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
