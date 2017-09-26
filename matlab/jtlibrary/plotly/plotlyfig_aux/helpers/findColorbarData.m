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
function colorbarDataIndex = findColorbarData(obj,colorbarIndex)
%locate index of data associated with colorbar
colorbarDataIndex = find(arrayfun(@(x)eq(x.AssociatedAxis,obj.State.Colorbar(colorbarIndex).AssociatedAxis),obj.State.Plot),1);
%if no matching data index found
if isempty(colorbarDataIndex)
    colorbarDataIndex = max(min(colorbarIndex,obj.State.Figure.NumPlots),1);
end
end