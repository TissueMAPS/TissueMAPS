function [OutputImage] = m_module(InputImage, varargin)
    
    import jtapi.*;

    fprintf('>>>>> Image has type "%s" and dimensions "%s".\n', ...
            char(class(InputImage)), mat2str(size(InputImage)));

    fprintf('>>>>> Pixel value at position (2, 3) (1-based): %d\n', ...
            InputImage(2, 3));

    data = struct();
    jtapi.writedata(data, varargin{1});

    OutputImage = InputImage;

end

