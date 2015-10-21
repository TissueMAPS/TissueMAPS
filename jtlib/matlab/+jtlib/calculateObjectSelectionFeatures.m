function [Area, Solidity, FormFactor] = calculateObjectSelectionFeatures(Objects)
    
    % Measure basic area/shape features
    props = regionprops(logical(Objects), 'Area', 'Solidity', 'Perimeter');

    % Features used for object selection
    Solidity = cat(1, props.Solidity);
    Area = cat(1, props.Area);
    tmp = log((4*pi*cat(1,props.Area)) ./ ((cat(1,props.Perimeter)+1).^2))*(-1);
    tmp(tmp<0) = 0;
    FormFactor = tmp;

end
