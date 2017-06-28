Jterator Matlab modules
=======================

This folder represents a Matlab *package* for Jterator modules. A module is a
.m file that defines a static class with constants and static methods.
The class must have the same name as the .m file, so module ``foo`` would be
defined in ``foo.m`` as follows:


.. code:: matlab

    classdef foo

        properties (Constant)

            VERSION = '0.1.0'

        end

        methods (Static)

            function [output_image, figure] = main(input_image, plot)

                if nargin < 2
                    plot = false;
                end

                figure = '';

                output_image = input_image;

            end

        end
    end


The module can be imported from the *jtmodules* package as follows:

.. code:: matlab

    import jtmodules.foo;
