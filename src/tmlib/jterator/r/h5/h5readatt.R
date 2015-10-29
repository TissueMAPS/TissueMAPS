# H5READ is a high level function based on the rhdf package.
# It reads the content of an attribute attached to a dataset within an hdf5 file.
#
# Usage 
#   	h5readatt(h5_file,h5_group,h5_attribute)
#
# Arguments 
#   	h5_file       		name of the hdf5 file (string)
#   	h5_group      	location of the dataset (string)
# 		h5_attribute	name of the attribute (string)
#
# Author
#   Markus Herrmann (2014)

h5readatt <- function(h5_file, h5_group, h5_attribute){

	fid <- H5Fopen(h5_file)
	did <- H5Dopen(fid, h5_group)
	
	if (H5Aexists(did, h5_attribute)) {
		aid <- H5Aopen(did, h5_attribute)
		attribute <- H5Aread(aid)
		return(attribute)
	}
	else{
	print ("attribute does not exist")
	}	

}
