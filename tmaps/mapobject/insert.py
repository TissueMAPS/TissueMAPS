"""
Insert mapobjects together with their outline coordinates into the PostGIS-enabled postgres database
based on the information stored in an experiment's data.h5 file.
This file can be run as a main module like this:
    $ python tmaps/mapobject/insert.py --dbuser robin --dbpass SOME_PASS --expid 1
"""
import sqlalchemy
import geoalchemy2

from tmaps.experiment import Experiment
from tmaps.mapobject import MapobjectOutline, Mapobject, MapobjectType, Feature, FeatureValue


def insert_mapobject_data(experiment_id, dbuser, dbpass, dbname='tissuemaps', dbport=5432):
    dburi = 'postgresql://%s:%s@localhost:%d/%s' % (dbuser, dbpass, dbport, dbname)
    engine = sqlalchemy.create_engine(dburi)
    smaker = sqlalchemy.orm.sessionmaker(bind=engine)
    session = smaker()
    e = session.query(Experiment).get(experiment_id)

    t = 0
    z = 0

    try:
        with e.dataset as data:

            mapobject_types = \
                [MapobjectType(name=n, experiment_id=experiment_id)
                 for n in data['/objects'].keys()]
            print 'Add MapobjectTypes'
            session.add_all(mapobject_types)
            session.flush()

            # A map to store the inserted MapObjects.
            # This map will later be used to add coordinates to all the inserted
            # objects. Since primary keys for the MapObjects are only available
            # once the rows are inserted into the db (commit step), this two-phase
            # insert is necessary.
            mapobjects_by_id = {}

            # First add all Mapobjects
            for mapobject_type in mapobject_types:
                object_name = mapobject_type.name
                mapobjects_by_id[mapobject_type.name] = {}
                object_data = data['/objects/%s' % object_name]
                external_object_ids = \
                    map(int, object_data['map_data/outlines/coordinates/'].keys())

                mapobjs = []
                for external_id in external_object_ids:
                    print 'Add Mapobject %d of type %s' % (external_id, object_name)
                    mapobj = Mapobject(
                        external_id=int(external_id),
                        mapobject_type_id=mapobject_type.id)
                    mapobjects_by_id[object_name][external_id] = mapobj
                    mapobjs.append(mapobj)

                session.add_all(mapobjs)

            # Insert all objects and generate ids
            print 'Flush Mapobjects to DB'
            session.flush()

    #         # Second add features for mapobjects
    #         for mapobject_type in mapobject_types:
    #             object_name = mapobject_type.name
    #             object_data = data['/objects/%s' % object_name]
    #             feature_data = object_data['features']
    #             features = \
    #                 [Feature(name=n, mapobject_type_id=mapobject_type.id)
    #                  for n in feature_data.keys()]
    #             session.add_all(features)
    #             session.flush()

    #             for feat in features:
    #                 feature_df = object_data['features/%s' % feat.name][()]
    #                 for row in feature_df

            # Third add outlines for all Mapobjects 
            for object_name in data['/objects']:
                outline_objects = []
                object_data = data['/objects/%s' % object_name]
                outline_group = \
                    object_data['map_data/outlines/coordinates/']
                for external_id in outline_group:
                    print 'Add MapObjectOutline for MapObject %d of type %s' \
                        % (int(external_id), object_name)

                    outline = outline_group[external_id]

                    # Create a string representation of the polygon using the EWKT
                    # format, e.g. "POLGON((1 2,3 4,6 7)))"
                    centroid = outline[()].mean(axis=0)
                    poly_ewkt = 'POLYGON((%s))' % ','.join(
                        ['%d %d' % tuple(p) for p in outline])
                    centroid_ewkt = 'POINT(%.2f %.2f)' % (centroid[0], centroid[1])
                    
                    mapobj = mapobjects_by_id[object_name][int(external_id)]

                    mapobj_outline = MapobjectOutline(
                        tpoint=t, zplane=z,
                        geom_poly=poly_ewkt,
                        geom_centroid=centroid_ewkt,
                        mapobject_id=mapobj.id)
                        

                    outline_objects.append(mapobj_outline)

                session.add_all(outline_objects)


        print 'Flush MapobjectOutlines to DB'
    except:
        session.rollback()
        print 'ERROR: Transaction rolled back.'
    else:
        print 'SUCCESS: Commit.'
        session.commit()

    return session


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

