import os.path as p
from contextlib import contextmanager

import h5py
from sqlalchemy import Column, String, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship

from tmlib.models.base import Model


SUPPORTED_MICROSCOPE_TYPES = set('cellvoyager', 'visiview')
SUPPORTED_PLATE_FORMATS = set([])  # TODO


# @exec_func_after_insert(_create_locations_if_necessary)
# @auto_remove_directory(lambda e: e.location)
class Experiment(Model):
    __tablename__ = 'experiments'

    name = Column(String)

    location = Column(String)
    description = Column(Text)

    microscope_type = Column(String)
    creation_stage = Column(String)
    plate_format = Column(Integer)

    def __init__(self, name, owner, microscope_type, plate_format,
                 description='', location=None):
        self.name = name
        self.description = description
        self.owner_id = owner.id

        if location is not None:
            if not p.isabs(location):
                raise ValueError(
                    'The experiments location on the filesystem must be '
                    'an absolute path'
                )
            else:
                self.location = location
        else:
            self.location = None

        self.creation_stage = 'WAITING_FOR_UPLOAD'

        if microscope_type not in SUPPORTED_MICROSCOPE_TYPES:
            raise ValueError('Unsupported microscope type')
        else:
            self.microscope_type = microscope_type

        if plate_format not in SUPPORTED_PLATE_FORMATS:
            raise ValueError('Unsupported plate format')
        else:
            self.plate_format = plate_format

    @property
    def dataset_path(self):
        return p.join(self.location, 'data.h5')

    @property
    def has_dataset(self):
        return p.exists(self.dataset_path)

    @property
    def plates_location(self):
        return p.join(self.location, 'plates')

    @property
    def plate_sources_location(self):
        return p.join(self.location, 'plate_sources')

    @property
    def channels_location(self):
        return p.join(self.location, 'channels')

    def belongs_to(self, user):
        return self.owner == user

    @property
    @contextmanager
    def dataset(self):
        fpath = self.dataset_path
        f = h5py.File(fpath, 'r')
        yield f
        f.close()

    @property
    def is_ready_for_image_conversion(self):
        all_plate_sources_ready = \
            all([pls.is_ready_for_processing for pls in self.plate_sources])
        is_ready = (
            self.creation_stage != 'CONVERTING_IMAGES'
            and all_plate_sources_ready
        )
        return is_ready

    def as_dict(self):
        mapobject_info = []
        for t in self.mapobject_types:
            # TODO: Change to this as soon as DB is ready
            # features = [f.name for f in t.features]
            with self.dataset as d:
                feature_names = d['/objects/%s/features' % t.name].keys()
                features = [{'name': n} for n in feature_names]
            mapobject_info.append({
                'mapobject_type_name': t.name,
                'features': features
            })

        return {
            'id': self.hash,
            'name': self.name,
            'description': self.description,
            'owner': self.owner.name,
            'plate_format': self.plate_format,
            'microscope_type': self.microscope_type,
            'creation_stage': self.creation_stage,
            'channels': [ch.as_dict() for ch in self.channels],
            'plate_sources': [pl.as_dict() for pl in self.plate_sources],
            'mapobject_info': mapobject_info,
            'plates': [pl.as_dict() for pl in self.plates]
        }

    def __repr__(self):
        return '<Experiment(id=%r, name=%r)>' % (self.id, self.name)
