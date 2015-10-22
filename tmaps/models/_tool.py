from xml.dom import minidom
import os
from tmaps.extensions.database import db
from sqlalchemy.dialects.postgresql import JSONB


class ToolInstance(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    # name = db.Column(db.String(80))
    # description = db.Column(db.Text)

    data_storage = db.Column(JSONB)

    tool_id = db.Column(db.String(80), nullable=False)
    appstate_id = db.Column(db.Integer, db.ForeignKey('appstate.id'),
                            nullable=False)
    experiment_id = db.Column(db.Integer, db.ForeignKey('experiment.id'),
                              nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'),
                        nullable=False)

    created_on = db.Column(db.DateTime, default=db.func.now())
    last_used_on = db.Column(db.DateTime, default=db.func.now())

    appstate = db.relationship(
        'AppStateBase', uselist=False, backref=db.backref(
            'tool_instances', cascade='all, delete-orphan'))

    experiment = db.relationship('Experiment', uselist=False)
    user = db.relationship('User', uselist=False)

    def __repr__(self):
        return '<ToolInstance %s : %d>' % (self.tool_id, self.id)

    def as_dict(self):
        return {
            'id': self.id,
            'tool_id': self.tool_id,
            'appstate_id': self.appstate_id,
            'experiment_id': self.experiment_id,
            'user_id': self.user_id
        }


class LayerMod(db.Model):
    """
    Instances of this class are created server-side by calling
    Tool.create_layermod(mofunc_name).

    """

    __tablename__ = 'layermod'

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(80), nullable=False)
    source = db.Column(db.String(80), nullable=False)
    tool_method_name = db.Column(db.String(80), nullable=False)
    tool_id = db.Column(db.String(80), nullable=False)
    experiment_id = db.Column(db.Integer, db.ForeignKey('experiment.id'),
                              nullable=False)
    appstate_id = db.Column(db.Integer, db.ForeignKey('appstate.id'),
                            nullable=False)

    render_args = db.Column(JSONB)
    modfunc_arg = db.Column(JSONB)

    experiment = db.relationship('Experiment', uselist=False)
    appstate = db.relationship(
        'AppStateBase', uselist=False, backref=db.backref(
            'layermods', cascade='all, delete-orphan'))

    created_on = db.Column(db.DateTime, default=db.func.now())
    last_used_on = db.Column(db.DateTime, default=db.func.now())

    def as_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'source': self.source,
            'tool_id': self.tool_id,
            'tool_method_name': self.tool_method_name,
            'render_args': self.render_args,
            'image_size': self.image_size
        }

    # TODO: Compute this upon creation
    @property
    def image_size(self):
        metainfo_file = os.path.join(
            self.experiment.location,
            'layermod_src',
            self.source,
            'ImageProperties.xml'
        )
        with open(metainfo_file, 'r') as f:
            dom = minidom.parse(f)
            width = int(dom.firstChild.getAttribute('WIDTH'))
            height = int(dom.firstChild.getAttribute('HEIGHT'))
            return [width, height]
