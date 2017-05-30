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
function obj = updateQuivergroup(obj, quiverIndex)

%-store original stair handle-%
quiver_group = obj.State.Plot(quiverIndex).Handle; 

%------------------------------------------------------------------------%

%-get children-%
quiver_child = get(quiver_group ,'Children'); 

%------------------------------------------------------------------------%

%xdata
xdata = []; 

%ydata 
ydata = []; 

%iterate through first two children (the vector line + arrow head)
for n = 1:2; 

%-update line -%
obj.State.Plot(quiverIndex).Handle = quiver_child(n);
updateLineseries(obj,quiverIndex); 

%update xdata
xdata = [xdata obj.data{quiverIndex}.x]; 

%update ydata
ydata = [ydata obj.data{quiverIndex}.y]; 

end

%------------------------------------------------------------------------%

% store the final data vector
obj.data{quiverIndex}.x = xdata; 
obj.data{quiverIndex}.y = ydata; 

%------------------------------------------------------------------------%

%-revert handle-%
obj.State.Plot(quiverIndex).Handle = quiver_group;

end