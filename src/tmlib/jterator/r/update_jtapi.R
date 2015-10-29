#! /usr/bin/env Rscript

library(devtools)
library(roxygen2)

setwd("/Users/mdh/jterator/src/jtapi/r/jtapi")
document()

setwd("..")
install("jtapi")

library(jtapi)
