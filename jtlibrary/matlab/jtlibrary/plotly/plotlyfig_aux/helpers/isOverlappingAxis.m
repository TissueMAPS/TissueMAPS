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
function [overlapping, overlapaxes] = isOverlappingAxis(obj, axIndex)

%-STANDARDIZE UNITS-%
axis_units = cell(1,axIndex);
for a = 1:axIndex
    axis_units{a} = get(obj.State.Axis(a).Handle,'Units');
    set(obj.State.Axis(a).Handle,'Units','normalized');
end

% check axis overlap
overlapaxes = find(arrayfun(@(x)(isequal(get(x.Handle,'Position'),get(obj.State.Axis(axIndex).Handle,'Position'))),obj.State.Axis(1:axIndex)));
overlapping = length(overlapaxes) > 1; %greater than 1 because obj.State.Axis(axIndex) will always be an overlapping axis

%-REVERT UNITS-%
for a = 1:axIndex
    set(obj.State.Axis(a).Handle,'Units',axis_units{a});
end

end
