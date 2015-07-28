#! /bin/sh

PROJECTDIR=$1

PROJECTNAME=${PROJECTDIR##*/}

CYCLES=$(find ${PROJECTDIR} -type d -regex ".*/${PROJECTNAME}[_-][0-9]+" | grep -Po "(?<=${PROJECTNAME}_).*")

for CYCLE in $CYCLES; do

	echo ""
	echo "processing cycle ${CYCLE}"

	illuminati -n 1 -l DAPI_${CYCLE} -sit --thresh-value=5000 -o ~/tissueMAPS/tmaps/expdata/${PROJECTNAME}/layers
	illuminati -n 2 -l RFP_${CYCLE} -sit --thresh-value=5000 -o ~/tissueMAPS/tmaps/expdata/${PROJECTNAME}/layers
	illuminati -n 3 -l GFP_${CYCLE} -sit --thresh-value=5000 -o ~/tissueMAPS/tmaps/expdata/${PROJECTNAME}/layers

done
