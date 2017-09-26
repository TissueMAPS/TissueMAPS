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
function [xsource, ysource, xoverlay, yoverlay] = findSourceAxis(obj, axIndex)

% initialize output
xsource = axIndex; 
ysource = axIndex;
xoverlay = false;
yoverlay = false;

% check axis overlap
[overlapping, overlapaxes] = isOverlappingAxis(obj, axIndex);

% find x/y source axis (takes non-identity overlapaxes as source)
if overlapping
    if isequal(get(obj.State.Axis(axIndex).Handle, 'XAxisLocation'), get(obj.State.Axis(overlapaxes(1)).Handle,'XAxisLocation'))
        xsource = overlapaxes(1);
    else
        xoverlay = overlapaxes(1);
    end
    if isequal(get(obj.State.Axis(axIndex).Handle, 'YAxisLocation'), get(obj.State.Axis(overlapaxes(1)).Handle,'YAxisLocation'))
        ysource = overlapaxes(1);
    else
        yoverlay = overlapaxes(1);
    end  
end

end