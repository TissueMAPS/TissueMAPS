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
function colorbarAxis = findColorbarAxis(obj,colorbarHandle)
if isHG2
    colorbarAxisIndex = find(arrayfun(@(x)(isequal(getappdata(x.Handle,'ColorbarPeerHandle'),colorbarHandle)),obj.State.Axis));
else
    colorbarAxisIndex = find(arrayfun(@(x)(isequal(getappdata(x.Handle,'LegendColorbarInnerList'),colorbarHandle) + ...
        isequal(getappdata(x.Handle,'LegendColorbarOuterList'),colorbarHandle)),obj.State.Axis));
end
colorbarAxis = obj.State.Axis(colorbarAxisIndex).Handle;
end