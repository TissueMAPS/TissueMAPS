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
