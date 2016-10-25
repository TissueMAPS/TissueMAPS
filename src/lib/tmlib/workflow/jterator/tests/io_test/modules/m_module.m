function [OutputImage] = m_module(InputImage, varargin)
    
    import jtlib.*;

    assert(isa(InputImage, 'uint16'), 'image has wrong data type')

    assert(isequal(size(InputImage), [3, 10, 10]), 'image has wrong dimensions')

    assert(InputImage(2, 3, 1) == 120, 'image has wrong value at index position')

    % fprintf('>>>>> Image has type "%s" and dimensions "%s".\n', ...
    %         char(class(InputImage)), mat2str(size(InputImage)));

    % fprintf('>>>>> Pixel value at position (2, 3) (1-based): %s\n', ...
    %         mat2str(squeeze(InputImage(2, 3, :))));

    data = struct();
    jtapi.writedata(data, varargin{1});

    OutputImage = InputImage;

end

