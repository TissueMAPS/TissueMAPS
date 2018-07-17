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
