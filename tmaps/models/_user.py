from ..extensions.database import db
from passlib.hash import sha256_crypt

from _appstate import AppStateShare
from _experiment import ExperimentShare
from ..extensions.encrypt import auto_generate_hash


@auto_generate_hash
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hash = db.Column(db.String(20))

    name = db.Column(db.String(80), index=True, unique=True,
                     nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

    active = db.Column(db.Boolean(), default=True)

    # both 'one to many'
    # owned_experiments = db.relationship("Experiment")

    created_on = db.Column(db.DateTime, default=db.func.now())
    updated_on = db.Column(db.DateTime, default=db.func.now(),
                           onupdate=db.func.now())

    def __init__(self, name, email, password, experiments=[]):

        self.name = name
        self.email = email
        self.password = sha256_crypt.encrypt(password)
        self.experiments = experiments

    def __repr__(self):
        return '<User %r>' % self.name

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
