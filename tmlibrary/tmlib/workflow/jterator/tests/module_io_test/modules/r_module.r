r_module <- new.env()

r_module$VERSION <- '0.0.1'

r_module$main <- function(input_image){

    stopifnot(all(input_image == floor(input_image)))

    stopifnot(dim(input_image) == c(10, 10, 3))

    stopifnot(input_image[3, 4, 1] == 69)

    output <- list()
    output[['output_image']] <- input_image

    return(output)
}
