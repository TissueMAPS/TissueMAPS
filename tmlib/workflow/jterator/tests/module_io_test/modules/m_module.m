classdef m_module

    properties (Constant)

        VERSION = '0.0.1'

    end

    methods (Static)

        function [output_image] = main(input_image)

            assert(isa(input_image, 'uint16'), 'image has wrong data type')

            assert(isequal(size(input_image), [10, 10, 3]), 'image has wrong dimensions')

            assert(input_image(3, 4, 1) == 69, 'image pixel has wrong value')

            output_image = input_image;

        end

    end

end
