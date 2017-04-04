#!/bin/sh -e

DATASET_NAME=$1  #Cellvoyager_2D_Multiplexing

DATA_DIR=$HOME/tmtestdata
USERNAME=storage
PASSWORD=o62ReU98h9Yb

echo "Download test dataset '$DATASET_NAME'..."
wget --user $USERNAME --password $PASSWORD -p -r -nH -np -R index.html* http://testdata.tissuemaps.org/storage/$DATASET_NAME -P $DATA_DIR

export TMTEST_DATASET_DIR="$DATA_DIR/storage/$DATASET_NAME"

exit 0
