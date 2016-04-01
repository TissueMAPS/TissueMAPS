"""
Insert mapobjects together with their outline coordinates into the PostGIS-enabled postgres database
based on the information stored in an experiment's data.h5 file.
This file can be run as a main module like this:
    $ python tmaps/mapobject/insert.py --dbuser robin --dbpass SOME_PASS --expid 1
"""
import os.path
import sqlalchemy
import geoalchemy2
from sqlalchemy.sql import func
import itertools
import h5py

from tmaps.experiment import Experiment
from tmaps.mapobject import (
    MapobjectOutline, Mapobject, MapobjectType, Feature, FeatureValue
)


N_POINTS_PER_TILE_LIMIT = 1500


def insert_mapobject_data(experiment_id, dbuser, dbpass, dbname='tissuemaps', dbport=5432):
    dburi = 'postgresql://%s:%s@localhost:%d/%s' % (dbuser, dbpass, dbport, dbname)
    engine = sqlalchemy.create_engine(dburi)
    smaker = sqlalchemy.orm.sessionmaker(bind=engine)
    session = smaker()
    e = session.query(Experiment).get(experiment_id)

    tpoint = 0
    zplane = 0

    try:
        data = h5py.File(os.path.join(e.location, 'data.h5'), 'r')

        mapobject_types = \
            [MapobjectType(name=n, experiment_id=e.id)
             for n in data['/objects'].keys()]
        print 'Add MapobjectTypes'
        session.add_all(mapobject_types)
        session.flush()

        # A map to store the inserted MapObjects.
        # This map will later be used to add coordinates to all the inserted
        # objects. Since primary keys for the MapObjects are only available
        # once the rows are inserted into the db (commit step), this two-phase
        # insert is necessary.
        mapobjects_by_external_id = {}

        # First add all Mapobjects
        for mapobject_type in mapobject_types:
            object_name = mapobject_type.name
            mapobjects_by_external_id[mapobject_type.name] = {}
            object_data = data['/objects/%s' % object_name]
            external_object_ids = object_data['ids'][()]
            has_is_border_info = 'is_border' in object_data
            if has_is_border_info:
                is_border = object_data['is_border'][()]
            mapobjs = []
            for external_id in external_object_ids:
                print 'Add Mapobject %d of type %s' % (external_id, object_name)
                if has_is_border_info:
                    is_border_obj = bool(is_border[external_id])
                else:
                    is_border_obj = False
                mapobj = Mapobject(
                    mapobject_type_id=mapobject_type.id,
                    is_border=is_border_obj)
                mapobjects_by_external_id[object_name][external_id] = mapobj
                mapobjs.append(mapobj)

            session.add_all(mapobjs)

        # Insert all objects and generate ids
        print 'Flush Mapobjects to DB'
        session.flush()

        # Second add features for mapobjects
        for mapobject_type in mapobject_types:
            print repr(mapobject_type)
            object_name = mapobject_type.name
            object_data = data['/objects/%s' % object_name]
            feature_data = object_data['features']
            features = [Feature(name=fname, mapobject_type_id=mapobject_type.id)
                        for fname in feature_data.keys()]
            print 'Add all %d features' % len(features)
            session.add_all(features)
            print 'Flush'
            session.flush()

            feature_values = []
            for feat in features:
                feature_arr = object_data['features/%s' % feat.name][()]
                for idx, val in enumerate(feature_arr):
                    mapobj = \
                        mapobjects_by_external_id[mapobject_type.name][idx]
                    feat_val = FeatureValue(
                        mapobject_id=mapobj.id,
                        value=val,
                        tpoint=0,
                        feature_id=feat.id)
                    feature_values.append(feat_val)
            print 'Flush feature values'
            session.flush()

        # Third add outlines for all Mapobjects 
        for mapobject_type in mapobject_types:
            object_name = mapobject_type.name
            outline_objects = []
            object_data = data['/objects/%s' % object_name]
            outline_group = \
                object_data['map_data/outlines/coordinates/']


            for external_id in outline_group:
                print 'Add MapObjectOutline for MapObject %d of type %s' \
                    % (int(external_id), object_name)

                outline = outline_group[external_id][()]

                # Create a string representation of the polygon using the EWKT
                # format, e.g. "POLGON((1 2,3 4,6 7)))"
                centroid = outline.mean(axis=0)
                poly_ewkt = 'POLYGON((%s))' % ','.join(
                    ['%d %d' % tuple(p) for p in outline])

                centroid_ewkt = 'POINT(%.2f %.2f)' % (centroid[0], centroid[1])
                
                mapobj = mapobjects_by_external_id[object_name][int(external_id)]

                mapobj_outline = MapobjectOutline(
                    tpoint=tpoint, zplane=zplane,
                    geom_poly=poly_ewkt,
                    geom_centroid=centroid_ewkt,
                    mapobject_id=mapobj.id)

                outline_objects.append(mapobj_outline)

            session.add_all(outline_objects)
            session.flush()

            max_z = 6
            n_points_in_tile_per_z = calculate_n_points_in_tile(
                session, max_z,
                mapobject_outline_ids=[o.id for o in outline_objects],
                n_tiles_to_sample=10)

            min_poly_zoom = min([z for z, n in n_points_in_tile_per_z.items()
                                 if n <= N_POINTS_PER_TILE_LIMIT])
            mapobject_type.min_poly_zoom = min_poly_zoom
            session.flush()




        print 'Flush MapobjectOutlines to DB'

    except:
        session.rollback()
        print 'ERROR: Transaction rolled back.'
        raise
    else:
        print 'SUCCESS: Commit.'
        session.commit()

    return session

def calculate_n_points_in_tile(session, max_z,
                               mapobject_outline_ids,
                               n_tiles_to_sample):
    import random

    n_points_in_tile_per_z = {}

    for z in range(max_z, -1, -1):
        tilesize = 256 * 2 ** (6 - z)

        rand_xs = [random.randrange(0, 2**z) for _ in range(n_tiles_to_sample)]
        rand_ys = [random.randrange(0, 2**z) for _ in range(n_tiles_to_sample)]

        n_points_in_tile_samples = []
        for x, y in zip(rand_xs, rand_ys):
            x0 = x * tilesize
            y0 = -y * tilesize

            minx = x0
            maxx = x0 + tilesize
            miny = y0 - tilesize
            maxy = y0

            tile = 'LINESTRING({maxx} {maxy},{minx} {maxy}, {minx} {miny}, {maxx} {miny}, {maxx} {maxy})'.format(
                minx=minx,
                maxx=maxx,
                miny=miny,
                maxy=maxy
            )

            n_points_in_tile = session.\
                query(func.sum(MapobjectOutline.geom_poly.ST_NPoints())).\
                filter(
                    (MapobjectOutline.id.in_(mapobject_outline_ids)) &
                    MapobjectOutline.geom_poly.intersects(tile)
                ).scalar()

            if n_points_in_tile is not None:
                n_points_in_tile_samples.append(n_points_in_tile)

        n_points_in_tile_per_z[z] = \
            float(sum(n_points_in_tile_samples)) / len(n_points_in_tile_samples)

    return n_points_in_tile_per_z


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Insert mapobject data into postgres')
    parser.add_argument('--expid', help='The id of the experiment', type=int)
    parser.add_argument('--dbname', help='The database name', default='tissuemaps')
    parser.add_argument('--dbuser', help='The database user')
    parser.add_argument('--dbpass', help='The database user\'s password')
    parser.add_argument('--dbport', help='The database port', type=int, default=5432)
    args = parser.parse_args()

    insert_mapobject_data(args.expid, args.dbuser, args.dbpass, args.dbname, args.dbport)

