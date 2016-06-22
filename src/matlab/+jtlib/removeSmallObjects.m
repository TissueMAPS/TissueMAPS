function OutputImage = removeSmallObjects(LabelImage, AreaThreshold)
    % OutputImage = removeSmallObjects(LabelImage, AreaThreshold)
    %
    % Remove objects smaller than a given area threshold from a labeled image.
    %
    % Input:
    %   LabelImage      A labeled image as produced by bwlabel() for example.
    %   AreaThreshold   An integer.
    %
    % Output:
    %   OutputImage     A labeled image.
    %
    % Author:
    %   Markus Herrmann

    % Ensure that the image is labeled properly
    % LabelImage = bwlabel(logical(LabelImage));

    props = regionprops(logical(LabelImage), 'Area');
    objArea2 = cat(1, props.Area);
    obj2remove = find(objArea2 < AreaThreshold);
    for j = 1:length(obj2remove)
        LabelImage(LabelImage == obj2remove(j)) = 0;
    end
    OutputImage = logical(LabelImage);

end
