import os
from .image_data import ImageData
from .metadata_reader import MetamorphMetadataReader


class MetamorphImageData(ImageData):

    '''
    Class for reading metadata files specific to microscopes equipped with
    Metamorph or Visitron software.

    Warning
    -------
    The *.stk* file format is in principle supported by Bio-Formats.
    However, if the *.nd* file is provided in the same folder, then the
    metadata of all files are read for each individual *.stk* file.
    To prevent this, the *.nd* file has to be separated from the *.stk* files,
    i.e. placed in another folder.
    '''

    metadata_formats = {'.nd'}

    def __init__(self, image_upload_folder, additional_upload_folder,
                 ome_xml_dir, experiment_dir, cfg, subexperiment=''):
        '''
        Initialize an instance of class ImageData.

        Parameters
        ----------
        image_upload_folder: str
            absolute path to directory where uploaded image files are located
        additional_upload_folder: str
            absolute path to directory where uploaded additional metadata files
            are located
        ome_xml_dir: str
            absolute path to directory where extracted ome-xml files are located
        experiment_dir: str
            absolute path to the corresponding experiment folder
        subexperiment: str, optional
            name of the subexperiment
            (only required in case the experiment has subexperiments)
        cfg: Dict[str, str]
            configuration settings

        See also
        --------
        `tmt.config`_
        '''
        super(MetamorphImageData, self).__init__(image_upload_folder,
                                                 additional_upload_folder,
                                                 ome_xml_dir,
                                                 experiment_dir,
                                                 cfg, subexperiment)
        self.image_upload_folder = image_upload_folder
        self.additional_upload_folder = additional_upload_folder
        self.ome_xml_dir = ome_xml_dir
        self.experiment_dir = experiment_dir
        self.subexperiment = subexperiment
        self.cfg = cfg

    @property
    def additional_files(self):
        '''
        Returns
        -------
        Dict[str, str] or None
            names of Visitron metadata files

        Raises
        ------
        OSError
            when no or an incorrect number of metadata files are found
        '''
        files = [f for f in os.listdir(self.additional_upload_folder)
                 if os.path.splitext(f)[1]
                 in MetamorphImageData.metadata_formats]
        if len(files) == 0:
            raise OSError('No metadata files found.')
        elif (len(files) > len(MetamorphImageData.metadata_formats)
                or (len(files) < len(MetamorphImageData.metadata_formats)
                    and len(files) > 0)):
            raise OSError('%d metadata files are required: "%s"'
                          % (len(MetamorphImageData.metadata_formats),
                             '", "'.join(MetamorphImageData.metadata_formats)))
        else:
            self._additional_files = dict()
            for md in MetamorphImageData.metadata_formats:
                self._additional_files[md] = [f for f in files
                                              if f.endswith(md)]
        return self._additional_files

    def read_additional_metadata(self):
        '''
        Returns
        -------
        bioformats.omexml.OMEXML
            metadata retrieved from Visitron microscope-specific files

        See also
        --------
        `metadata_reader.VisitronMetadataReader`_
        '''
        with MetamorphMetadataReader() as reader:
            nd_path = os.path.join(self.additional_upload_folder,
                                   self.additional_files['.nd'][0])
            self.ome_additional_metadata = reader.read(nd_path)
        return self.ome_additional_metadata
