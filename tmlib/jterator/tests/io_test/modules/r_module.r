library(jtapi)

r_module <- function(InputImage, ...){

    dots <- list(...)

    cat(sprintf('>>>>> Image has type "%s" and dimensions "%s".\n',
          		toString(typeof(InputImage)), toString(dim(InputImage))))

    cat(sprintf('>>>>> Pixel value at position [2, 3] (1-based): %s\n',
                toString(InputImage[2, 3, ])))

    data <- list()
    jtapi::writedata(data, dots$data_file)

    output <- list()
    output[['OutputImage']] <- InputImage

    return(output)
}
