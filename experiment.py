import json
import os.path as p
import os
from xml.dom import minidom

import h5py

from app import EXPDATA_DIR_LOCATION


class Experiment(object):

    """A class for holding information and measurement data about experiment,
    i.e. collections of layers that can be visualized in the TissueMAPS client.

    Objects of this class are (normally) created from expinfo.json files that
    reside in the respective experiment directories.

    Each time a tool is invoked, the right Experiment object will be passed to
    it.

    """

    default_expinfo_file = {
        'name': None,
        'position_mapper': {
            'id': 'default',
            'config': {}
        },
        'outline_layers': {
            'names': []
        },
        'feature_set': {
            'location': 'features.h5'
        }
    }

    def __init__(self, name, layers, posmapper_cfg, feature_set):
        self.name = name
        self.posmapper_cfg = posmapper_cfg
        self.feature_set = feature_set
        self.layers = layers


    def serialize_for_tmaps(self):
        """Create a dictionary from this experiment that may later be serialized
        to JSON and sent to the client."""

        serialized_layers = [l.serialize_for_tmaps() for l in self.layers]
        return {
            'experiment_name': self.name,
            'layers': serialized_layers
        }


    @staticmethod
    def create_from_expinfo(experiment_name):
        """Find the expinfo.json file for the Experiment with name
        `experiment_name`. If such a file can't be found, some default settings
        are used."""
        experiment_dir = p.join(EXPDATA_DIR_LOCATION, experiment_name)

        # Load settings specific for this experiment if an expinfo.json file
        # exists and use its settings to override the default ones.
        fpath = p.join(experiment_dir, 'expinfo.json')
        expinfo = Experiment.default_expinfo_file
        if p.exists(fpath):
            with open(fpath, 'r') as f:
                expinfo_new = json.load(f)
                expinfo.update(expinfo_new)


        # Position Mapper
        posmapper_cfg = expinfo['position_mapper']

        # Feature Set
        featureset_fpath = p.join(experiment_dir, expinfo['feature_set']['location'])
        if p.exists(featureset_fpath):
            feature_set  = h5py.File(featureset_fpath, 'r')
        else:
            feature_set = None

        # Layers
        layers = []

        layers_dir = p.join(experiment_dir, 'layers')
        layer_names = [name for name in os.listdir(layers_dir)
                       if p.isdir(p.join(layers_dir, name))]

        for layer_name in layer_names:
            layer_dir = p.join(layers_dir, layer_name)
            metainfo_file = p.join(layer_dir, 'ImageProperties.xml')

            if p.exists(metainfo_file):
                with open(metainfo_file, 'r') as f:
                    dom = minidom.parse(f)
                    width = int(dom.firstChild.getAttribute('WIDTH'))
                    height = int(dom.firstChild.getAttribute('HEIGHT'))

                is_outline_layer = False
                if 'names' in expinfo['outline_layers']:
                    for mask_name in expinfo['outline_layers']['names']:
                        if layer_name == mask_name:
                            is_outline_layer = True

                if 'suffix' in expinfo['outline_layers']:
                    is_outline_layer = \
                        layer_name.endswith(expinfo['outline_layers']['suffix'])


                rel_layer_dir = layer_dir.replace(EXPDATA_DIR_LOCATION, '')
                pyramid_path = '/expdata' + rel_layer_dir

                layer = Layer(layer_name, is_outline_layer, width, height, pyramid_path)
                layers.append(layer)
            else:
                continue

        return Experiment(experiment_name, layers, posmapper_cfg, feature_set)

    @staticmethod
    def get_all_experiments():
        """Return an Experiment object for each directory in the expdata folder."""

        experiment_names = [name for name in os.listdir(EXPDATA_DIR_LOCATION)
                            if p.isdir(p.join(EXPDATA_DIR_LOCATION, name))]
        experiments = {}
        for name in experiment_names:
            experiments[name] = Experiment.create_from_expinfo(name)

        return experiments


class Layer(object):

    """A small wrapper class for layers in an experiment."""

    def __init__(self, name, is_mask, width, height, pyramid_path):
        self.name = name
        self.is_mask = is_mask
        self.width = width
        self.height = height
        self.pyramid_path = pyramid_path

    def serialize_for_tmaps(self):
        # Create json that can be sent to the client
        return {
            'layer_name': self.name,
            'pyramid_path': self.pyramid_path,
            'width': self.width,
            'height': self.height,
            'is_outline_layer': self.is_mask
        }


# TODO: It probably makes sense to create a separate class for this.
# In the future there could be added support for other formats which could be
# specified in the expinfo.file. As long as all the feature sets adhere to the
# same interface.
class HDF5FeatureSet(object):

    """Class for FeatureSets wrapping an HDF5 file"""

    def __init__(self, filename):
        """
        :filename: The filename of the HDF5 data set.

        """

        self._dataset = h5py.File(filename, 'r')
