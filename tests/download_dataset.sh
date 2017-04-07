#!/bin/sh -e

EXPERIMENT_NAME=$1

DATA_DIR=$HOME/tmtestdata
USERNAME=storage
PASSWORD=o62ReU98h9Yb

echo "Download test dataset '$EXPERIMENT_NAME'..."
wget --user $USERNAME --password $PASSWORD -p -r -nH -np -R index.html* http://data.tissuemaps.org/storage/$EXPERIMENT_NAME -P $DATA_DIR

export TMTEST_DATASET_DIR="$DATA_DIR/storage/$EXPERIMENT_NAME"

exit 0
