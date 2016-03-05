"""
Insert mapobjects together with their outline coordinates into the PostGIS-enabled postgres database
based on the information stored in an experiment's data.h5 file.
This file can be run as a main module like this:
    $ python tmaps/mapobject/insert.py --dbuser robin --dbpass SOME_PASS --expid 1
"""
import sqlalchemy
import geoalchemy2

from tmaps.experiment import Experiment
from tmaps.mapobject import MapobjectCoords, Mapobject


def insert_mapobject_data(experiment_id, dbuser, dbpass, dbname='tissuemaps', dbport=5432):
    dburi = 'postgresql://%s:%s@localhost:%d/%s' % (dbuser, dbpass, dbport, dbname)
    engine = sqlalchemy.create_engine(dburi)
    smaker = sqlalchemy.orm.sessionmaker(bind=engine)
    session = smaker()
    e = session.query(Experiment).get(experiment_id)

    t = 0
    z = 0

    with e.dataset as data:

        # A map to store the inserted MapObjects.
        # This map will later be used to add coordinates to all the inserted
        # objects. Since primary keys for the MapObjects are only available
        # once the rows are inserted into the db (commit step), this two-phase
        # insert is necessary.
        mapobjects_by_id = {}

        # First add all MapObjects
        for object_name in data['/objects']:
            mapobjects_by_id[object_name] = {}
            object_data = data['/objects/%s' % object_name]
            object_ids = \
                map(int, object_data['map_data/outlines/coordinates/'].keys())

            mapobjs = []
            for id in object_ids:
                print 'Add MapObject %d of type %s' % (id, object_name)
                mapobj = Mapobject(
                    external_id=int(id), name=object_name, experiment_id=e.id) 
                mapobjects_by_id[object_name][mapobj.external_id] = mapobj
                mapobjs.append(mapobj)

            session.add_all(mapobjs)

        # Insert all objects and generate ids
        print 'Commit MapObjects to DB'
        session.commit()

        # Second add coordinates for all MapObjects 
        for object_name in data['/objects']:
            coord_objects = []
            object_data = data['/objects/%s' % object_name]
            coord_group = \
                object_data['map_data/outlines/coordinates/']
            for id in coord_group:
                print 'Add MapObjectCoords for MapObject %d of type %s' \
                    % (int(id), object_name)

                coord = coord_group[id]

                # Create a string representation of the polygon using the EWKT
                # format, e.g. "POLGON((1 2,3 4,6 7)))"
                poly_ewkt = 'POLYGON((%s))' % ','.join(
                    ['%d %d' % tuple(p) for p in coord])

                mapobj = mapobjects_by_id[object_name][int(id)]

                mapobj_coords = MapobjectCoords(
                    time=t, z_level=z, geom=poly_ewkt,
                    mapobject_id=mapobj.id)
                    

                coord_objects.append(mapobj_coords)

            session.add_all(coord_objects)
    print 'Commit MapObjectCoords to DB'
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

