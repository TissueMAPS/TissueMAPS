from flask import current_app


class Spark(object):
    def __init__(self, app=None):
        """
        A extension that creates a spark context that can be used to submit
        computational tasks with Apache Spark.
        This extension should be initialized via its `init_app` method, e.g.:

        spark = Spark()
        app.init_app(app)
        spark.ctx.parallelize(['spark', 'test']).count()

        Parameters
        ----------
        app : flask.Flask, optional
            A flask application object. The preferred way to intialize
            the application via the `init_app` method.

        """
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """
        Initialize the extension for some flask application. This will create
        a spark context using information provided in the flask configuration.
        The relevant configuration keys are:

        USE_SPARK, default False
        SPARK_MASTER_URL, default 'local'
        SPARK_DB_URL, default 'postgresql://localhost:5432/tissuemaps'
        SPARK_APP_NAME, default 'spark'

        If `USE_SPARK` is falsy, the ctx and sqlctx properties will be None.

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
            ctx = SparkContext(conf=conf)
            sqlctx = SQLContext(ctx)
            app.extensions['spark'] = {
                'context': ctx,
                'sqlcontext': sqlctx
            }

    @property
    def ctx(self):
        """
        pyspark.SparkContext
            The spark context. If `USE_SPARK` is set to a falsy value this
            property will be None.

        """
        return current_app.extensions.get('spark', {}).get('context')

    @property
    def sqlctx(self):
        """
        pyspark.SQLContext
            The spark sql context. If `USE_SPARK` is set to a falsy value
            this property will be None.

        """
        return current_app.extensions.get('spark', {}).get('sqlcontext')
