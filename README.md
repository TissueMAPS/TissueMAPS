# TissueMAPS Toolbox #

[tmt](tmt) is a Python package of image processing tools required for [TissueMAPS](https://github.com/HackerMD/TissueMAPS).

The package is configured via a YAML configuration settings file [tmt.config](tmt/tmt.config).

It contains several sub-packages, which are all dependent on these configurations.

## [align](tmp/align) ##

A package for aligning images between different acquisition cycles.

## [illuminati](tmp/illuminati) ##

A package for creating pyramid images.

## [visi](tmp/visi) ##

A package for converting Visitron's STK files to PNG images with optional renaming.

## [datafusion](tmp/datafusion) ##

A package for fusing data produced by [Jterator](https://github.com/HackerMD/Jterator).


*For more details, please refer to the individual tools.*
