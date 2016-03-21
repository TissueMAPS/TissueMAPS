#!/usr/bin/env python
import argparse

import tmlib.models


def create_tables():
    engine = tmlib.models.utils.create_tmaps_database_engine()
    # Create all tables defined by declarative classes in tmlib.models
    tmlib.models.Model.metadata.create_all(engine)

if __name__ == '__main__':

    parser = argparse.ArgumentParser('Create tables in TissueMAPS database.')

    args = parser.parse_args()

    create_tables()
