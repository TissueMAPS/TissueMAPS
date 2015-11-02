import os
import os.path as p
from sqlalchemy import event
from werkzeug import secure_filename
from ..extensions.database import db
from utils import auto_remove_directory, auto_create_directory
from tmaps.models import Experiment
import shutil
from tmlib import source as tmlib_source
from . import Model, CRUDMixin


ACQUISITION_UPLOAD_STATUS = (
    'UPLOADING',
    'WAITING',
    'SUCCESSFUL',
    'FAILED'
)


def _acquisition_loc(index, plate_id):
    """Return the directory path for a acquisition"""
    pls = PlateSource.get(plate_id)
    dirname = tmlib_source.PlateAcquisition.ACQUISITION_DIR_FORMAT.\
                           format(index=index)
    return p.join(pls.location, dirname)


def _get_free_index(existing_acquisitions):
    used_indices = set([aq.index for aq in existing_acquisitions])
    free_indices = set(range(len(used_indices) + 1)) - used_indices
    return sorted(free_indices)[0]


@auto_create_directory(lambda t: _acquisition_loc(t.index, t.plate_source_id))
@auto_remove_directory(lambda pl: pl.location)
class PlateAcquisition(Model, CRUDMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), index=True)
    index = db.Column(db.Integer)
    description = db.Column(db.Text)

    upload_status = db.Column(db.Enum(*ACQUISITION_UPLOAD_STATUS,
                              name='upload_status'))

    plate_source_id = db.Column(db.Integer, db.ForeignKey('plate_source.id'))

    plate_source = db.relationship('PlateSource', backref='acquisitions')

    created_on = db.Column(db.DateTime, default=db.func.now())

    def __init__(self, name, plate_source, description=''):
        self.index = _get_free_index(plate_source.acquisitions)
        self.name = name
        self.description = description
        self.plate_source_id = plate_source.id
        self.upload_status = 'WAITING'

    @property
    def tmlib_object(self):
        return tmlib_source.PlateAcquisition(self.location)

    @property
    def location(self):
        return _acquisition_loc(self.index, self.plate_source_id)

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
        fname = secure_filename(f.filename)
        fpath = p.join(self.tmlib_object.image_dir, fname)
        f.save(fpath)
        return fname

    def remove_files(self):
        files = [p.join(self.tmlib_object.image_dir, f) for f in self.files]
        for f in files:
            os.remove(f)
        self.upload_status = 'WAITING'
        db.session.commit()

    @property
    def images_location(self):
        return self.tmlib_object.image_dir

    def as_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'files': self.files,
            'upload_status': self.upload_status
        }


def _plate_source_loc(id, name, experiment_id):
    """Return the directory path for a plate"""
    e = Experiment.query.get(experiment_id)
    sec_name = secure_filename(name)
    dirname = tmlib_source.PlateSource.PLATE_SOURCE_DIR_FORMAT.\
                           format(name=sec_name)
    dirname = '%s__%d' % (dirname, id)
    return p.join(e.plate_sources_location, dirname)



@auto_create_directory(lambda t: _plate_source_loc(t.id, t.name, t.experiment_id))
@auto_remove_directory(lambda pl: pl.location)
class PlateSource(Model, CRUDMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), index=True)
    description = db.Column(db.Text)

    experiment_id = db.Column(db.Integer, db.ForeignKey('experiment.id'))

    experiment = db.relationship('Experiment', backref='plate_sources')

    def __init__(self, name, experiment, description=''):
        self.name = name
        self.description = description
        self.experiment_id = experiment.id

    @property
    def tmlib_object(self):
        # FIXME: Is the second argument necessary?
        return tmlib_source.PlateSource(self.location)

    @property
    def location(self):
        return _plate_source_loc(self.id, self.name, self.experiment.id)

    @property
    def is_ready_for_processing(self):
        aqs_ready = all([aq.is_ready_for_processing for aq in self.acquisitions])
        return len(self.acquisitions) != 0 and aqs_ready

    def as_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'acquisitions': [a.as_dict() for a in self.acquisitions]
        }
