from flask import current_app


# TODO: How relevant are these notes?
# BEGIN
# Download the PostgreSQL JDBC Driver from
# https://jdbc.postgresql.org/download.html. Export the environment
# variable 'SPARK_CLASSPATH' when working in the pyspark shell or use
# '--driver-class-path' flag when submitting the script via the command
# line with spark-submit
# END
class Spark(object):
    def __init__(self, app=None):
        """A extension that creates a spark context that can be used to submit
        computational tasks with Apache Spark.
        This extension should be initialized via its `init_app` method, e.g.:

        spark = Spark()
        app.init_app(app)
        spark.sc.parallelize(['spark', 'test']).count()

        Parameters
        ----------
        app : flask.Flask, optional
            A flask application object. The preferred way to intialize
            the application via the `init_app` method.

        """
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Initialize the extension for some flask application. This will create
        a spark context using information provided in the flask configuration.
        The relevant configuration keys are:

        - USE_SPARK, default False
            If `USE_SPARK` is falsy, the sc and sqlc properties will be
            None.
        - SPARK_MASTER_URL, default 'local'
        - SPARK_DB_URL, default 'postgresql://localhost:5432/tissuemaps'
            User information should be provided according to the following
            syntax:
            'postgresql://localhost:5432/tissuemaps?user=USER&password=PW'
        - SPARK_APP_NAME, default 'spark'

        Parameters
        ----------
        app : flask.Flask
            A flask application object.

        """
        from pyspark import SparkConf
        from pyspark import SparkContext
        from pyspark.sql import SQLContext

        app.config.setdefault('SPARK_MASTER_URL', 'local')
        app.config.setdefault(
            'SPARK_DB_URL', 'postgresql://localhost:5432/tissuemaps')
        app.config.setdefault('SPARK_APP_NAME', 'spark')
        use_spark = app.config.get('USE_SPARK')

        if use_spark:
            conf = SparkConf()
            conf.setAppName(app.config['SPARK_APP_NAME'])
            conf.setMaster(app.config['SPARK_MASTER_URL'])
            conf.set(
                'spark.serializer',
                'org.apache.spark.serializer.KryoSerializer'
            )
            sc = SparkContext(conf=conf)
            sqlc = SQLContext(sc)
            app.extensions['spark'] = {
                'context': sc,
                'sqlcontext': sqlc
            }

    @property
    def sc(self):
        """
        pyspark.SparkContext
            The spark context. If `USE_SPARK` is set to a falsy value this
            property will be None.

        """
        return current_app.extensions.get('spark', {}).get('context')

    @property
    def sqlc(self):
        """
        pyspark.SQLContext
            The spark sql context. If `USE_SPARK` is set to a falsy value
            this property will be None.

        """
        return current_app.extensions.get('spark', {}).get('sqlcontext')

    def df_reader(self, *args, **kwargs):
        from pyspark.sql import DataFrameReader

        db_url = current_app.config.get('SPARK_DB_URL')
        kwargs.setdefault('url', db_url)
        return DataFrameReader(self.sqlctx).jdbc(*args, **kwargs)

    def read_table(self, table_name):
        """Reads an SQL table for use with Apache Spark.

        Parameters
        ----------
        table_name : str
            Name of the SQL table

        Returns
        -------
        pyspark.sql.DataFrame

        Note
        ----
        Caches the :py:class:`pyspark.sql.DataFrame` to speed up computations.

        """
        return self.df_reader(table=table_name).cache()
