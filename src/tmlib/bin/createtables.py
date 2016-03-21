#!/usr/bin/env python
import argparse

import tmlib.models
from tmlib.db_utils import create_tmaps_database_engine


def create_tables():
    engine = create_tmaps_database_engine()
    # Create all tables defined by declarative classes in tmlib.models
    tmlib.models.Model.metadata.create_all(engine)

if __name__ == '__main__':

    parser = argparse.ArgumentParser('Create tables in TissueMAPS database.')

    args = parser.parse_args()

    create_tables()
