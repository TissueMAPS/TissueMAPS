# from models import *

# def test_appstate_creation(dbsession):
#     json = '{}'

#     user = User.query.filter_by(name='testuser').first()
#     st = AppState(name='some name', blueprint=json, owner_id=user.id)
#     dbsession.add(st)
#     dbsession.commit()

#     assert st.owner_id == user.id
#     assert st.owner.id == user.id
#     assert user.appstates[0].id == st.id


# def test_snapshot_creation(dbsession):

#     user = User.query.filter_by(name='testuser').first()

#     st = AppState(
#         name='somename',
#         blueprint='{}',
#         owner_id=user.id,
#         description='')

#     dbsession.add(st)
#     dbsession.commit()

#     assert st.is_snapshot == False

#     snap = st.create_snapshot()

#     assert st.id != snap.id
#     assert st.name == snap.name
#     assert st.blueprint == snap.blueprint
#     assert st.owner_id == snap.owner_id
#     assert st.description == snap.description
#     assert st.id == snap.parent_appstate_id

#     assert len(st.tool_instances) == len(snap.tool_instances)
#     assert len(st.layermods) == len(snap.layermods)

#     snap_toolinst_ids = {t.id for t in snap.tool_instances}
#     for t in st.tool_instances:
#         assert not t.id in snap_toolinst_ids

#     snap_layermod_ids = {l.id for l in snap.layermods}
#     for l in st.layermods:
#         assert not l.id in snap_layermod_ids
