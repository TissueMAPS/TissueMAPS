import os
import os.path as p

from tmaps.extensions.database import db
from passlib.hash import sha256_crypt

from werkzeug import secure_filename
from tmaps.appstate import Appstate
from tmaps.experiment import ExperimentShare
from tmaps.model import CRUDMixin, Model
from tmaps.model.decorators import auto_generate_hash, auto_create_directory


def _experiments_dir(user_location):
    expdir_loc = p.join(user_location, 'experiments')
    return expdir_loc


@auto_create_directory(lambda t: t.location)
@auto_create_directory(lambda t: _experiments_dir(t.location))
@auto_generate_hash
class User(Model, CRUDMixin):
    id = db.Column(db.Integer, primary_key=True)
    hash = db.Column(db.String(20))

    name = db.Column(db.String(80), index=True, unique=True,
                     nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

    location = db.Column(db.String(300))

    active = db.Column(db.Boolean(), default=True)

    created_on = db.Column(db.DateTime, default=db.func.now())
    updated_on = db.Column(db.DateTime, default=db.func.now(),
                           onupdate=db.func.now())

    def __init__(self, name, email, password, location, experiments=[]):

        self.name = name
        self.email = email
        self.location = location
        if not p.exists(location):
            os.mkdir(location)
        self.password = sha256_crypt.encrypt(password)
        self.experiments = experiments

    def __repr__(self):
        return '<User %r>' % self.name

    @property
    def experiments_location(self):
        return _experiments_dir(self.location)


    @property
    def received_appstates(self):
        shares = AppStateShare.query.filter_by(recipient_user_id=self.id)
        return [share.appstate for share in shares]

    @property
    def received_experiments(self):
        shares = ExperimentShare.query.\
            filter_by(recipient_user_id=self.id).\
            all()
        experiments = [sh.experiment for sh in shares]
        return experiments
