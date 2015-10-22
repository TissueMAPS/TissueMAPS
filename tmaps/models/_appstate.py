from ..extensions.database import db
from sqlalchemy.dialects.postgresql import JSON
from _tool import ToolInstance, LayerMod
from ..extensions.encrypt import auto_generate_hash

class AppStateShare(db.Model):
    __tablename__ = 'appstate_share'

    id = db.Column(db.Integer, primary_key=True)

    recipient_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    donor_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    appstate_id = db.Column(db.Integer, db.ForeignKey('appstate.id'))

    appstate = db.relationship('AppState', uselist=False)
    recipient = db.relationship('User', uselist=False,
                                foreign_keys=[recipient_user_id])
    donor = db.relationship('User', uselist=False,
                            foreign_keys=[donor_user_id])
    # access_level = db.Column(db.Enum(*EXPERIMENT_ACCESS_LEVELS,
    #                                  name='access_level'))


class AppStateBase(db.Model):
    __tablename__ = 'appstate'

    id = db.Column(db.Integer, primary_key=True)
    hash = db.Column(db.String(20))

    name = db.Column(db.String(80), nullable=False)
    blueprint = db.Column(JSON, nullable=False)

    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    description = db.Column(db.Text)

    created_on = db.Column(db.DateTime, default=db.func.now())
    last_used_on = db.Column(db.DateTime, default=db.func.now())

    owner = db.relationship('User', backref='appstates')

    type = db.Column(db.String(20))

    __mapper_args__ = {
        'polymorphic_on': type,
        'polymorphic_identity': 'appstate'
    }

    @property
    def is_snapshot(self):
        return self.type == 'snapshot'

    def __repr__(self):
        return '<AppState %s>' % self.name

    def is_editable_by_user(self, user):
        was_shared_with_user = AppStateShare.query.filter_by(
            recipient_user_id=user.id, appstate_id=self.id)
        belongs_to_user = user.id == self.owner.id
        not_a_snapshot = not self.is_snapshot
        return not_a_snapshot and (belongs_to_user or was_shared_with_user)

    def as_dict(self):
        return {
            'id': self.hash,
            'name': self.name,
            'description': self.description,
            'blueprint': self.blueprint,
            'owner': self.owner.name,
            'is_snapshot': self.is_snapshot,
            'created_on': self.is_snapshot
        }


@auto_generate_hash
class AppStateSnapshot(AppStateBase):

    parent_appstate_id = db.Column(db.Integer, db.ForeignKey('appstate.id'))

    appstate = db.relationship('AppState', uselist=False)

    __mapper_args__ = {
        'polymorphic_identity': 'snapshot'
    }


@auto_generate_hash
class AppState(AppStateBase):

    __mapper_args__ = {
        'polymorphic_identity': 'standard'
    }

    def create_snapshot(self):
        st = AppStateSnapshot(
            name=self.name,
            blueprint=self.blueprint,
            owner_id=self.owner_id,
            description=self.description,
            parent_appstate_id=self.id
        )

        db.session.add(st)
        db.session.commit()

        for t in self.tool_instances:
            clone = ToolInstance(
                data=t.data,
                tool_id=t.tool_id,
                appstate_id=st.id,
                experiment_id=t.experiment_id,
                user_id=self.owner_id
            )
            st.tool_instances.append(clone)

        for l in self.layermods:
            clone = LayerMod(
                layer_name = l.layer_name,
                tool_method_name = l.tool_method_name,
                tool_id = l.tool_id,
                experiment_id = l.experiment_id,
                appstate_id = st.id,
                render_args = l.render_args,
                modfunc_arg = l.modfunc_arg
            )
            st.layermods.append(clone)

        db.session.commit()

        return st

