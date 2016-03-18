import os.path as p

from sqlalchemy import Column, String, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship

from tmlib.models.base import Model


# @auto_create_directory(lambda t: _plate_loc(t.name, t.experiment_id))
# @auto_remove_directory(lambda pl: pl.location)
class Plate(Model):
    __tablename__ = 'plates'

    name = Column(String, index=True)
    description = Column(Text)

    experiment_id = Column(Integer, ForeignKey('experiments.id'))
    experiment = relationship('Experiment', backref='plates')

    def __init__(self, name, description, experiment):
        self.name = name
        self.description = description
        self.experiment_id = experiment.id

    @property
    def location(self):
        return p.join(self.experiment.plates_location, self.name)

    @property
    def is_ready_for_processing(self):
        # TODO
        return False

    def as_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description
        }
