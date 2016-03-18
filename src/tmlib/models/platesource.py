import os
import os.path as p

from sqlalchemy import Column, String, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship

from tmlib.models.base import Model


ACQUISITION_UPLOAD_STATUS = (
    'UPLOADING',
    'WAITING',
    'SUCCESSFUL',
    'FAILED'
)


def _get_free_index(existing_acquisitions):
    used_indices = set([aq.index for aq in existing_acquisitions])
    free_indices = set(range(len(used_indices) + 1)) - used_indices
    return sorted(free_indices)[0]


# @auto_create_directory(lambda t: _acquisition_loc(t.index, t.plate_source_id))
# @auto_remove_directory(lambda pl: pl.location)
class PlateAcquisition(Model):
    __tablename__ = 'plate_acquisitions'

    name = Column(String, index=True)
    index = Column(Integer)
    description = Column(Text)

    upload_status = Column(String)

    plate_source_id = Column(Integer, ForeignKey('plate_sources.id'))
    plate_source = relationship('PlateSource', backref='acquisitions')

    def __init__(self, name, plate_source, description=''):
        self.index = _get_free_index(plate_source.acquisitions)
        self.name = name
        self.description = description
        self.plate_source_id = plate_source.id
        self.upload_status = 'WAITING'

    @property
    def location(self):
        return p.join(
            self.plate_source.acquisitions_location,
            'acqusition_%03d' % self.index)

    @property
    def files(self):
        try:
            files = self.tmlib_object.image_files
            return files
        except OSError:
            return []

    @property
    def is_ready_for_processing(self):
        # TODO: Files might be uploading, this is only checked client-side!
        return len(self.files) != 0 and self.upload_status == 'SUCCESSFUL'

    def save_file(self, f):
        # fname = secure_filename(f.filename)
        # TODO: Create secure filename
        fname = f.filename
        fpath = p.join(self.tmlib_object.image_dir, fname)
        f.save(fpath)
        return fname

    def remove_files(self, session):
        files = [p.join(self.tmlib_object.image_dir, f) for f in self.files]
        for f in files:
            os.remove(f)
        self.upload_status = 'WAITING'
        session.commit()

    @property
    def images_location(self):
        return p.join(self.location, 'images')

    def as_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'files': self.files,
            'upload_status': self.upload_status
        }


# @auto_create_directory(lambda t: _plate_source_loc(t.id, t.name, t.experiment_id))
# @auto_remove_directory(lambda pl: pl.location)
class PlateSource(Model):
    __tablename__ = 'plate_sources'

    name = Column(String, index=True)
    description = Column(Text)

    experiment_id = Column(Integer, ForeignKey('experiments.id'))
    experiment = relationship('Experiment', backref='plate_sources')

    def __init__(self, name, experiment, description=''):
        self.name = name
        self.description = description
        self.experiment_id = experiment.id

    @property
    def location(self):
        # TODO
        return p.join(
            self.experiment.plate_sources_location,
            'plate_source_%03d' % self.id)

    @property
    def is_ready_for_processing(self):
        aqs_ready = all(
            [aq.is_ready_for_processing for aq in self.acquisitions])
        return len(self.acquisitions) != 0 and aqs_ready

    def as_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'acquisitions': [a.as_dict() for a in self.acquisitions]
        }
