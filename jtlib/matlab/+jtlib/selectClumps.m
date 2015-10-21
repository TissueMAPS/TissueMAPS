function [objects2Cut, objectsNot2Cut] = selectObjectsForCutting(objects, maxSolidity, minFormFactor, maxArea, minArea)

    import jtlib.rplabel;
    import jtlib.calculateObjectSelectionFeatures;

    [area, solidity, formFactor] = calculateObjectSelectionFeatures(objects);

    % Select objects based on these features (user defined thresholds)
    obj2cut = solidity < maxSolidity & formFactor > minFormFactor & ...
                  area < maxArea     &       area > minArea;
    objNot2cut = ~obj2cut;
                
    objSelected = zeros(size(obj2cut));
    objSelected(obj2cut) = 1;
    objSelected(objNot2cut) = 2;
    selectedObjects = rplabel(logical(objects),[],objSelected);

    % Create mask image with objects selected for cutting
    objects2Cut = zeros(size(objects));
    objects2Cut(selectedObjects==1) = 1;
    objects2Cut = logical(objects2Cut);

    % Store remaining objects that are omitted from cutting
    objectsNot2Cut = zeros(size(objects));
    objectsNot2Cut(selectedObjects==2) = 1;
    objectsNot2Cut = logical(objectsNot2Cut);

end
