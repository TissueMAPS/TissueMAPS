# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2016  Markus D. Herrmann, University of Zurich and Robin Hafen
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''Base classes for classification tools.'''
import logging
import argparse
import numpy as np
import pandas as pd
from abc import ABCMeta
from abc import abstractmethod
from abc import abstractproperty

import tmlib.models as tm
from tmlib import cfg
from tmlib import __version__
from tmlib.utils import same_docstring_as, autocreate_directory_property
from tmlib.readers import JsonReader
from tmlib.logging_utils import configure_logging, map_logging_verbosity
from tmlib.tools import SUPPORTED_TOOLS
from tmlib.tools import get_tool_class

logger = logging.getLogger(__name__)


LOGO = '''
    )           (
 ( /(           )\
 )\()) (    (  ((_)
(_))/  )\   )\  _     TissueMAPS tool request manager (tmlib %s)
| |_  ((_) ((_)| |    https://github.com/TissueMAPS/TmLibrary
|  _|/ _ \/ _ \| |
 \__|\___/\___/|_|

''' % __version__


class _ToolMeta(ABCMeta):

    '''Metaclass for creation of :class:`tmlib.tools.Tool`.'''

    def __init__(self, name, bases, d):
        if name == 'Tool':
            return
        required_attrs = {'__icon__', '__description__'}
        is_abstract = getattr(self, '__abstract__', False)
        for attr in required_attrs:
            if not hasattr(self, attr) and not is_abstract:
                raise AttributeError(
                    'Class "%s" is derived from base class "Tool" '
                    'and must implement attribute "%s".' % (name, attr)
                )


class Tool(object):

    '''Abstract base class for a tool.'''

    __metaclass__ = _ToolMeta

    __abstract__ = True

    def __init__(self, experiment_id):
        '''
        Parameters
        ----------
        experiment_id: int
            ID of the experiment for which the tool request is made
        '''
        self.experiment_id = experiment_id
        self.use_spark = cfg.use_spark
        if self.use_spark:
            self._create_spark_context()
        else:
            self.sc = None
            self.sqlc = None

    def _create_spark_context(self):
        '''Creates a Spark Context.'''
        from pyspark import SparkConf
        from pyspark import SparkContext
        conf = SparkConf()
        conf.setAppName(cls.__name__)
        # py_files = []
        # conf.set('spark.submit.pyFiles', ','.join(py_files))
        self.sc = SparkContext(conf=conf)
        from pyspark.sql import SQLContext
        self.sqlc = SQLContext(sc)

    def _df_reader(self, *args, **kwargs):
        '''Reads data from a SQL table via
        :class:`pyspark.sql.DataFrameReader`.

        Note
        ----
        Requires installation and configuration of a
        `Postgres JDBC driver <https://jdbc.postgresql.org/>`_ as well as
        the enviroment variable ``SPARK_DB_URL`` set according to the pattern
        ``"postgresql://{host}:5432/tissuemaps?user={user}&password={password}"``.
        '''
        from pyspark.sql import DataFrameReader
        try:
            db_url = os.environ['SPARK_DB_URL']
        except KeyError:
            raise OSError('Environment variable "SPARK_DB_URL" not set.')
        except:
            raise
        db_url = db_url.replace(
            'tissuemaps', 'tissuemaps_experiment_%s' % self.experiment_id
        )
        kwargs.setdefault('url', 'jdbc:%s' % db_url)
        return DataFrameReader(self.sqlc).jdbc(*args, **kwargs)

    def _read_table(self, table_name):
        '''Reads a SQL table for use with Apache Spark.

        Parameters
        ----------
        table_name: str
            name of the SQL table or aliased SQL query

        Returns
        -------
        pyspark.sql.DataFrame

        Note
        ----
        Caches the :class:`pyspark.sql.DataFrame` to speed up computations.

        '''
        return self._df_reader(table=table_name).cache()

    def _build_batch_filename_for_job(self, submission_id):
        batches_location = os.path.join(self.tools_location, 'batches')
        filename = '%s_%d.json' % (self.__class__.__name__, submission_id)
        return os.path.join(batches_location, filename)

    def _build_command(self, submission_id):
        if self.use_spark:
            command = ['spark-submit', '--master', cfg.spark_master]
            if cfg.spark_master == 'yarn':
                command.extend(['--deploy-mode', 'client'])
            # TODO: ship Python dependencies
            # args.extend([
            #     '--py-files', cfg.spark_tmlib.tools_egg
            # ])
        else:
            args = []
        command.extend([
            'tm_tool', str(self.experiment_id),
            '--name', tool_name,
            '--submission_id', str(submission_id)
        ])
        return command

    def create_job(self, submission_id, user_name,
            duration='00:30:00', memory=3800, cores=1):
        '''Creates a job for asynchroneous processing of a client tool request.

        Parameters
        ----------
        submission_id: int
            ID of the corresponding submission
        user_name: str
            name of the submitting user
        duration: str, optional
            computational time that should be allocated for the job
            in HH:MM:SS format (default: ``"00:30:00"``)
        memory: int, optional
            amount of memory in Megabyte that should be allocated for the job
            (default: ``3800``)
        cores: int, optional
            number of CPU cores that should be allocated for the job
            (default: ``1``)

        Returns
        -------
        tmlib.workflow.jobs.ToolJob
            tool job
        '''
        logger.info('create tool job for submission %d', submission_id)
        logger.debug('allocated time for job: %s', duration)
        logger.debug('allocated memory for job: %d MB', memory)
        logger.debug('allocated cores for job: %d', cores)
        job = ToolJob(
            tool_name=self.__class__.__name__,
            arguments=self._build_command(submission_id),
            output_dir=self.log_location,
            submission_id=submission_id,
            user_name=user_name
        )
        job.requested_walltime = Duration(duration)
        job.requested_memory = Memory(memory, Memory.MB)
        if not isinstance(cores, int):
            raise TypeError(
                'Argument "cores" must have type int.'
            )
        if not cores > 0:
            raise ValueError(
                'The value of "cores" must be positive.'
            )
        job.requested_cores = cores
        return job

    def read_batch_file(self, submission_id):
        '''Reads job description from JSON file.

        Parameters
        ----------
        submission_id: int
            ID of the respective submission

        Returns
        -------
        dict
            batch

        Raises
        ------
        OSError
            when `filename` does not exist
        '''
        filename = self._build_batch_filename_for_job(submission_id)
        if not os.path.exists(filename):
            raise OSError(
                'Job description file does not exist: %s.' % filename
            )
        with JsonReader(filename) as f:
            batch = f.read()
        return batch

    @autocreate_directory_property
    def log_location(self):
        '''str: location where log files are stored'''
        return os.path.join(self.tools_location, 'log')

    @autocreate_directory_property
    def batches_location(self):
        '''str: location where job description files are stored'''
        return os.path.join(self.tools_location, 'batches')

    def write_batch_file(self, batch, submission_id):
        '''Writes job description to file in JSON format.

        Parameters
        ----------
        batch: dict
            job description as a mapping of key-value pairs
        submission_id: int
            ID of the corresponding submission

        Raises
        ------
        TypeError
            when `batch` is not a mapping
        '''
        if not isinstance(batch, dict):
            raise TypeError(
                'Job description must have type dict.'
            )
        batch_file = self._build_batch_filename_for_job(submission_id)
        with JsonWriter(batch_file) as f:
            f.write(batch)

    @staticmethod
    def _build_feature_values_query(mapobject_type_name, feature_name):
        # We run the actual query in SQL, since this performs way better
        # compared to loading the table and then filtering it via Spark
        # NOTE: the alias is required for compatibility with DataFrameReader
        return '''
            (SELECT v.value, v.mapobject_id FROM feature_values AS v
            JOIN features AS f ON f.id=v.feature_id
            JOIN mapobject_types AS t ON t.id=f.mapobject_type_id
            WHERE f.name=\'{feature_name}\'
            AND t.name=\'{mapobject_type_name}\'
            ) AS t
        '''.format(
            mapobject_type_name=secure_filename(mapobject_type_name),
            feature_name=secure_filename(feature_name)
        )

    def get_feature_values(self, mapobject_type_name, feature_name):
        '''Selects all values from table "feature_values" for mapobjects of
        a given :class:`tmlib.models.MapbojectType` and
        :class:`tmlib.models.Feature`.

        Parameters
        ----------
        mapobject_type_name: str
            name of the parent mapobject type
        feature_name: str
            name of the parent feature

        Returns
        -------
        pyspark.sql.DataFrame or pandas.DataFrame
            data frame with columns "mapobject_id" and "value" and a row for
            each mapobject
        '''
        if self.use_spark:
            return _get_feature_values_spark(mapobject_type_name, feature_name)
        else:
            return _get_feature_values_sklearn(mapobject_type_name, feature_name)

    def _get_feature_values_spark(self, mapobject_type_name, feature_name):
        query = self._build_feature_values_query(
            mapobject_type_name, feature_name
        )
        return self._read_table(query)

    def _get_feature_values_sklearn(self, mapobject_type_name, feature_name):
        with tm.utils.ExperimentSession(self.experiment_id) as session:
            feature_values = session.query(
                    tm.FeatureValue.mapobject_id, tm.FeatureValue.value
                ).\
                join(tm.Feature).\
                join(tm.MapobjectType).\
                filter(
                    tm.Feature.name == feature_name,
                    tm.MapobjectType.name == mapobject_type_name
                ).\
                all()
        return pd.DataFrame(feature_values, columns=['mapobject_id', 'value'])

    @abstractmethod
    def process_request(self, payload):
        '''Processes a tool request sent by the client.

        Parameters
        ----------
        payload: dict
            an arbitrary mapping sent by the client tool

        '''
        pass

    def main(cls):
        '''Main entry point for command line interface.

        Parsers the command line arguments and configures logging.

        Returns
        -------
        int
            ``0`` when program completes successfully and ``1`` otherwise

        Raises
        ------
        SystemExit
            exitcode ``1`` when the call raises an :class:`Exception`

        Warning
        -------
        Don't do any other logging configuration anywhere else!
        '''
        parser = argparse.ArgumentParser()
        parser.description = '''
            TissueMAPS command line interface for asynchronous processing of
            client tool requests.
        '''
        parser.add_argument(
            'experiment_id', type=int,
            help='ID of the experiment that should be processed'
        )
        parser.add_argument(
            '--verbosity', '-v', action='count', default=0,
            help='increase logging verbosity'
        )
        parser.add_argument(
            '--name', '-n', required=True,
            choices=SUPPORTED_TOOLS, help='name of the tool'
        )
        parser.add_argument(
            '--submission_id', '-s', type=int, required=True,
            help='ID of the corresponding tool job submission'
        )

        args = parser.parse_args()

        configure_logging()
        level = map_logging_verbosity(args.verbosity)
        lib_logger = logging.getLogger('tmlib')
        lib_logger.setLevel(level)
        tool_logger.debug('processing on node: %s', socket.gethostname())

        tool_cls = get_tool_class(args.name)
        tool = tool_cls(args.experiment_id)
        payload = tool.read_batch_file(args.submission_id)
        print LOGO
        tool.process_request(payload)


class Classifier(Tool):

    '''Abstract base class for classification tools.'''

    __abstract__ = True

    @same_docstring_as(Tool.__init__)
    def __init__(self, experiment_id, submission_id):
        super(Classifier, self).__init__(experiment_id, submission_id)

    def format_feature_data(self, mapobject_type_name, feature_names):
        '''Loads feature values from database and bring the dataset into the
        format required by classifiers.

        Parameters
        ----------
        mapobject_type_name: str
            name of the selected mapobject type, see
            :class:`tmlib.models.mapobject.MapobjectType`
        feature_names: List[str]
            names of selected features, see
            :class:`tmlib.models.mapobject.Feature`

        Returns
        -------
        pyspark.sql.DataFrame or pandas.DataFrame
            data frame where columns are features and rows are mapobjects
            indexable by `mapobject_ids` (*pandas* dataframes have a separate
            column for each feature with the name of the respective feature,
            while *spark* dataframes have only one column named "feature" with
            :class:`pyspark.mllib.linalg.DenseVector` as required by classifiers
            of the :mod:`pyspark.ml` package)
        '''

    def _format_feature_data_sklearn(self, mapobject_type_name, feature_names):
        with tm.utils.ExperimentSession(self.experiment_id) as session:
            mapobject_type_id = session.query(tm.MapobjectType.id).\
                filter_by(name=mapobject_type_name).\
                one()
            feature_values = session.query(
                    tm.Feature.name, tm.FeatureValue.mapobject_id, tm.FeatureValue.value
                ).\
                join(tm.FeatureValue).\
                filter(
                    (tm.Feature.name.in_(feature_names)) &
                    (tm.Feature.mapobject_type_id == mapobject_type_id)).\
                all()
        feature_df_long = pd.DataFrame(feature_values)
        feature_df_long.columns = ['features', 'mapobject', 'value']
        return pd.pivot_table(
            feature_df_long, values='value', index='mapobject',
            columns='features'
        )

    def _format_feature_data_spark(self, mapobject_type_name, feature_names):
        # feature_values = spark.read_table('feature_values')
        # features = spark.read_table('features')
        # mapobjects = spark.read_table('mapobjects')
        # mapobject_types = spark.read_table('mapobject_types')
        for i, name in enumerate(feature_names):
            df = self.get_feature_values_spark(mapobject_type_name, name)
            # df = feature_values.\
            #     join(features, features.id==feature_values.feature_id).\
            #     join(mapobjects, mapobjects.id==feature_values.mapobject_id).\
            #     join(mapobject_types, mapobject_types.id==features.mapobject_type_id).\
            #     filter(features.name == name).\
            #     filter(mapobject_types.name == mapobject_type_name).\
            #     filter(mapobject_types.experiment_id == experiment_id)
            if i == 0:
                data = df.select(
                    df.value.alias(name),
                    df.mapobject_id
                )
            else:
                df = df.select(
                    df.value.alias(name),
                    df.mapobject_id.alias('%s_mapobject_id' % name)
                )
                on = data['mapobject_id'] == df['%s_mapobject_id' % name]
                data = data.join(df, on, 'inner').drop('%s_mapobject_id' % name)

        assembler = VectorAssembler(
            inputCols=feature_names, outputCol='features'
        )
        return assembler.transform(data).select('features', 'mapobject_id')

