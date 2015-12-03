import os
import pandas as pd
import tempfile
from tmlib.experiment import Experiment

experiment_dir = '/Users/mdh/shares/tmaps-share1/testdata/MOTC_PreTest4'
exp = Experiment(experiment_dir)
md = exp.plates[0].cycles[0].image_metadata_table

tmp_dir = tempfile.gettempdir()
tables_file = os.path.join(tmp_dir, 'tables.h5')

# Store the metadata table in the HDF5 file
store = pd.HDFStore(tables_file)
store.append('metadata', md, format='table', data_columns=True)

# Query the metadata table and select only a subset of the data
md_subset = store.select('metadata', columns=['name', 'zplane_ix'], where='channel_ix==0 and tpoint_ix==0')
