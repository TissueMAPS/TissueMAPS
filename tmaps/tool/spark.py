import os
from pyspark.sql.functions import udf, col
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.clustering import KMeans

# NOTE:
# 1. Download the PostgreSQL JDBC Driver from https://jdbc.postgresql.org/download.html
# 2. Export the environment variable "SPARK_CLASSPATH=<path-to-driver-jar>"


db_url = 'postgresql://localhost:5432/tissuemaps'
feature_values = sqlContext.read.format("jdbc").\
    options(url="jdbc:%s" % db_url, dbtable='feature_values').\
    load()

features = sqlContext.read.format("jdbc").\
    options(url="jdbc:%s" % db_url, dbtable='features').\
    load()

mapobjects = sqlContext.read.format("jdbc").\
    options(url="jdbc:%s" % db_url, dbtable='mapobjects').\
    load()

mapobject_types = sqlContext.read.format("jdbc").\
    options(url="jdbc:%s" % db_url, dbtable='mapobject_types').\
    load()

feature_names = ['Morphology_area', 'Morphology_eccentricity']
mapobject_type_name = 'Cells'
experiment_id = 1
for i, name in enumerate(feature_names):
    df = feature_values.\
        join(features, features.id==feature_values.feature_id).\
        join(mapobjects, mapobjects.id==feature_values.mapobject_id).\
        join(mapobject_types, mapobject_types.id==features.mapobject_type_id).\
        filter(features.name == name).\
        filter(mapobject_types.name == mapobject_type_name).\
        filter(mapobject_types.experiment_id == experiment_id).\
        select(
            feature_values.value.alias(name),
            feature_values.mapobject_id.alias('%s_mapobject_id' % name)
        )
    if i == 0:
        data = df
    else:
        ref_name = feature_names[0]
        on = data['%s_mapobject_id' % ref_name] == df['%s_mapobject_id' % name]
        data = data.join(df, on, 'inner')

assembler = VectorAssembler(inputCols=feature_names, outputCol="features")
selected_features = assembler.transform(data).select('features')

kmeans = Kmeans(k=2, seed=1)
model = kmeans.fit(selected_features)
transformed = model.transform(selected_features).select('prediction')
result = transformed.collect()
labels = [r.prediction for r in result]
