function imLabel = rplabel(imLogical, imIntensity, Property, logarithm)

%REGIONPROPS_LABEL_IMAGE creates a label image based on a measurement of
%the regionprops function.
%
%   When PROPERTY is provided as string:
%   L = REGIONPROPS_LABEL_IMAGE(BW,I,PROPERTY,LOGARITHM) calls the
%   regionprops function using the input images BW and I and the input
%   property PROPERTY. It returns a matrix L, of the same size as BW,
%   containing labels of the measured PROPERTY for the connected objects in
%   BW.
%
%   When PROPERTY is provided as matrix:
%   L = REGIONPROPS_LABEL_IMAGE(BW,I,PROPERTY,LOGARITHM) returns matrix L
%   whithout calling the regionprops function.
%
%   Input:
%   - BW: binary image
%   - I: intensity image, if you don't want to measure intensities provide
%     empty matrix [] as second input
%   - PROPERTY: string, e.g. 'Area', 'Eccentricity', 'MeanIntensity', etc.
%     or matrix (when properties were already calculated)
%   - LOGARITHM (optional): string, either 'two' for log2, 'ten' for log10,
%     or 'nat' for log
%
%   Output:
%   IMLABEL: label image containing labels of the measured property.
%   (Optionally, output is given in logarithmic form.)


if isempty(imIntensity)
    imIntensity = zeros(size(imLogical));
end

if nargin == 3
    useLog = false;
elseif nargin == 4
    useLog = true;
end

if ischar(Property)
    matProperty = cell2mat(struct2cell(regionprops(imLogical,imIntensity,Property)))';
elseif ismatrix(Property)
    matProperty = Property;
end
imLabel = bwlabel(imLogical);
Index = unique(imLabel);
Index(Index==0) = [];
for t = 1:length(Index)
    if useLog
        if strcmp(logarithm,'two')
            imLabel(imLabel==Index(t)) = log2(matProperty(t));
        elseif strcmp(logarithm,'ten')
            imLabel(imLabel==Index(t)) = log10(matProperty(t));
        elseif strcmp(logarithm,'nat')
            imLabel(imLabel==Index(t)) = log(matProperty(t));
        end
    else
        imLabel(imLabel==Index(t)) = matProperty(t);
    end
end
