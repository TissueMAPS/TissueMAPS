from tmaps.model import Model

from sqlalchemy import Integer, ForeignKey, Column, Text, String
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship


class Appstate(Model):
    __tablename__ = 'appstates'

    name = Column(String(80), nullable=False)
    blueprint = Column(JSON, nullable=False)

    owner_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    description = Column(Text)

    owner = relationship('User', backref='appstates')

    type = Column(String(20))

    # @property
    # def is_snapshot(self):
    #     return self.type == 'snapshot'

    # def __repr__(self):
    #     return '<AppState %s>' % self.name

    # def is_editable_by_user(self, user):
    #     was_shared_with_user = AppStateShare.query.filter_by(
    #         recipient_user_id=user.id, appstate_id=self.id)
    #     belongs_to_user = user.id == self.owner.id
    #     not_a_snapshot = not self.is_snapshot
    #     return not_a_snapshot and (belongs_to_user or was_shared_with_user)

    # def as_dict(self):
    #     return {
    #         'id': self.hash,
    #         'name': self.name,
    #         'description': self.description,
    #         'blueprint': self.blueprint,
    #         'owner': self.owner.name,
    #         'is_snapshot': self.is_snapshot,
    #         'created_on': self.is_snapshot
    #     }

# class AppStateShare(Model):
#     __tablename__ = 'appstate_share'

#     id = Column(Integer, primary_key=True)

#     recipient_user_id = Column(Integer, ForeignKey('user.id'))
#     donor_user_id = Column(Integer, ForeignKey('user.id'))
#     appstate_id = Column(Integer, ForeignKey('appstate.id'))

#     appstate = relationship('AppState', uselist=False)
#     recipient = relationship('User', uselist=False,
#                                 foreign_keys=[recipient_user_id])
#     donor = relationship('User', uselist=False,
#                             foreign_keys=[donor_user_id])
#     # access_level = Column(Enum(*EXPERIMENT_ACCESS_LEVELS,
#     #                                  name='access_level'))



# @auto_generate_hash
# class AppStateSnapshot(AppStateBase):

#     parent_appstate_id = Column(Integer, ForeignKey('appstate.id'))

#     appstate = relationship('AppState', uselist=False)

#     __mapper_args__ = {
#         'polymorphic_identity': 'snapshot'
#     }


# @auto_generate_hash
# class AppState(AppStateBase):

#     __mapper_args__ = {
#         'polymorphic_identity': 'standard'
#     }

#     def create_snapshot(self):
#         st = AppStateSnapshot(
#             name=self.name,
#             blueprint=self.blueprint,
#             owner_id=self.owner_id,
#             description=self.description,
#             parent_appstate_id=self.id
#         )

#         session.add(st)
#         session.commit()

#         # for t in self.tool_instances:
#         #     clone = ToolInstance(
#         #         data=t.data,
#         #         tool_id=t.tool_id,
#         #         appstate_id=st.id,
#         #         experiment_id=t.experiment_id,
#         #         user_id=self.owner_id
#         #     )
#         #     st.tool_instances.append(clone)

#         # for l in self.layermods:
#         #     clone = LayerMod(
#         #         layer_name = l.layer_name,
#         #         tool_method_name = l.tool_method_name,
#         #         tool_id = l.tool_id,
#         #         experiment_id = l.experiment_id,
#         #         appstate_id = st.id,
#         #         render_args = l.render_args,
#         #         modfunc_arg = l.modfunc_arg
#         #     )
#         #     st.layermods.append(clone)

#         session.commit()

#         return st

