 #' Reading configuration settings from YAML string.
#'
#' @param configuration string, configuration settings
#' @return list
readconfig <- function(configuration) {

    require(yaml)

    rfilename <- "readconfig"

    config <- yaml.load_file(configuration)
    cat(sprintf("jt -- %s: read configuration settings from \"%s\"\n",
                rfilename, configuration))

    return(config)
}

#' Writing data to HDF5 file.
#'
#' @param data list, data output that should be written to HDF5 file.
#' @param data_file string, path to the HDF5 file.
writedata <- function(data, data_file) {

    require(rhdf5)

    rfilename <- "writedata"

    hdf5_filename <- data_file

    for (key in names(data)) {
      if (!is.null(dim(data[[key]]))) {
        out <- t(data[[key]])
      }
      else {
        out <- data[[key]]
      }
      hdf5_location <- key
      h5createDataset(hdf5_filename, hdf5_location, 
                      dims = dim(out),
                      storage.mode = storage.mode(out))
      h5write(out, hdf5_filename, hdf5_location)
      cat(sprintf("jt -- %s: wrote dataset '%s' to HDF5 location: \"%s\"\n",
                rfilename, key, hdf5_location))
    }
}
