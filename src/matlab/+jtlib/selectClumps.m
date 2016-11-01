% Copyright 2016 Markus D. Herrmann, University of Zurich
% 
% Licensed under the Apache License, Version 2.0 (the "License");
% you may not use this file except in compliance with the License.
% You may obtain a copy of the License at
% 
%     http://www.apache.org/licenses/LICENSE-2.0
% 
% Unless required by applicable law or agreed to in writing, software
% distributed under the License is distributed on an "AS IS" BASIS,
% WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
% See the License for the specific language governing permissions and
% limitations under the License.
function [objects2Cut, objectsNot2Cut] = selectClumps(objects, maxSolidity, minFormFactor, maxArea, minArea)

    import jtlib.plotting;
    import jtlib.calculateObjectSelectionFeatures;

    [area, solidity, formFactor] = jtlib.calculateObjectSelectionFeatures(objects);

    % Select objects based on these features (user defined thresholds)
    obj2cut = solidity < maxSolidity & formFactor > minFormFactor & ...
                  area < maxArea     &       area > minArea;
    objNot2cut = ~obj2cut;
                
    objSelected = zeros(size(obj2cut));
    objSelected(obj2cut) = 1;
    objSelected(objNot2cut) = 2;
    selectedObjects = jtlib.plotting.rplabel(logical(objects),[],objSelected);

    % Create mask image with objects selected for cutting
    objects2Cut = zeros(size(objects));
    objects2Cut(selectedObjects==1) = 1;
    objects2Cut = logical(objects2Cut);

    % Store remaining objects that are omitted from cutting
    objectsNot2Cut = zeros(size(objects));
    objectsNot2Cut(selectedObjects==2) = 1;
    objectsNot2Cut = logical(objectsNot2Cut);

end
