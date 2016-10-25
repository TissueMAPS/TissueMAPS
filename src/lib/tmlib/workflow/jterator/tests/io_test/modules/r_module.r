library(jtlib)

r_module <- function(InputImage, ...){

    dots <- list(...)

    stopifnot(all(InputImage == floor(InputImage)))

    stopifnot(dim(InputImage) == c(3, 10, 10))

    stopifnot(InputImage[2, 3, 1] == 120)

    # cat(sprintf('>>>>> Image has type "%s" and dimensions "%s".\n',
    #       		toString(typeof(InputImage)), toString(dim(InputImage))))

    # cat(sprintf('>>>>> Pixel value at position [2, 3] (1-based): %s\n',
    #             toString(InputImage[2, 3, ])))

    output <- list()
    output[['OutputImage']] <- InputImage

    return(output)
}
