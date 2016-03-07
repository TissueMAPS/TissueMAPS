from tmaps.extensions.database import db
from tmaps.model import CRUDMixin, Model
from tmaps.mapobject import Mapobject, MapobjectCoords
import geoalchemy2.functions as geofun


class LabelResult(Model, CRUDMixin):
    id = db.Column(db.Integer, primary_key=True)
    mapobject_name = db.Column(db.String(120))
    tool_session_id = \
        db.Column(db.Integer, db.ForeignKey('tool_session.id'))

    def __init__(self, ids, labels, mapobject_name, session):
        self.mapobject_name = mapobject_name
        self.tool_session_id = session.id

        db.session.add(self)
        db.session.flush()

        label_objs = []
        ids = Mapobject.translate_external_ids(
            ids, session.experiment_id, mapobject_name)
        for ext_id, label in zip(ids, labels):
            pl = LabelResultLabel(
                mapobject_id=ext_id, label=label,
                classification_result_id=self.id)
            label_objs.append(pl)

        db.session.add_all(label_objs)
        db.session.commit()

    def to_dict(self):
        return {
            'id': self.id
        }

    def get_labelled_mapobject_coords_within_tile(self, x, y, z,
                                                  zlevel, time,
                                                  centroid=False):
        if not centroid:
            select_stmt = \
                db.session.query(MapobjectCoords.mapobject_id,
                                 LabelResultLabel.label,
                                 MapobjectCoords.geom.ST_AsGeoJSON())
        else:
            select_stmt = \
                db.session.query(MapobjectCoords.mapobject_id,
                                 LabelResultLabel.label,
                                 MapobjectCoords.geom.ST_Centroid().ST_AsGeoJSON())
        return select_stmt.\
            join(Mapobject).\
            join(LabelResultLabel).\
            join(LabelResult).\
            filter(
                (LabelResult.id == self.id) &
                (Mapobject.name == self.mapobject_name) &
                (MapobjectCoords.time == time) &
                (MapobjectCoords.z_level == zlevel) &
                MapobjectCoords.intersection_filter(x, y, z)
            ).all()


class LabelResultLabel(Model, CRUDMixin):
    id = db.Column(db.Integer, primary_key=True)
    mapobject_id = db.Column(db.Integer, db.ForeignKey('mapobject.id'))
    classification_result_id = \
        db.Column(db.Integer, db.ForeignKey('label_result.id'))

    result = db.relationship('LabelResult', backref='labels')
    mapobject = db.relationship('Mapobject', backref='labels')
    label = db.Column(db.Integer)
