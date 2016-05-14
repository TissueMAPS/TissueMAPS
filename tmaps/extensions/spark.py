from pyspark import SparkConf
from pyspark import SparkContext
from pyspark.sql import SQLContext

# NOTE: in DEBUG mode the context get's created twice
# set spark.driver.allowMultipleContexts = true in the spark-defaults.conf file
conf = SparkConf()
conf.setAppName('tmaps')
conf.set('spark.serializer', 'org.apache.spark.serializer.KryoSerializer')
sc = SparkContext(conf=conf)
sqlc = SQLContext(sc)

