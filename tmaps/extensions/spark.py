from pyspark import SparkConf
from pyspark import SparkContext
from pyspark.sql import SQLContext

# NOTE: in DEBUG mode the context get's created twice
# set spark.driver.allowMultipleContexts = true in the spark-defaults.conf file
master_url = 'local'
db_url = 'postgresql://localhost:5432/tissuemaps?user=markus&password=123'

conf = SparkConf()
conf.setAppName('tmaps')
conf.setMaster(master_url)
conf.set('spark.serializer', 'org.apache.spark.serializer.KryoSerializer')

sc = SparkContext(conf=conf)
sqlc = SQLContext(sc)

