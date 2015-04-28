#! /bin/sh

PROJECTDIR=$1

PROJECTNAME=${PROJECTDIR##*/}

CYCLES=$(find ${PROJECTDIR} -type d -regex ".*/${PROJECTNAME}[_-][0-9]+" | grep -Po "(?<=${PROJECTNAME}_).*")

for CYCLE in $CYCLES; do

	echo ""
	echo "processing cycle ${CYCLE}"

	illuminati ${PROJECTDIR}/${PROJECTNAME}*${CYCLE}/TIFF/*DAPI*png -sit --thresh-value=5000 -o ~/tissueMAPS/tmaps/expdata/${PROJECTNAME}/layers/DAPI_cycle${CYCLE}
	illuminati ${PROJECTDIR}/${PROJECTNAME}*${CYCLE}/TIFF/*RFP*png -sit --thresh-value=3000 -o ~/tissueMAPS/tmaps/expdata/${PROJECTNAME}/layers/EEA1_cycle${CYCLE}
	illuminati ${PROJECTDIR}/${PROJECTNAME}*${CYCLE}/TIFF/*GFP*png -sit --thresh-value=5000 -o ~/tissueMAPS/tmaps/expdata/${PROJECTNAME}/layers/Tubulin_cycle${CYCLE}

done
