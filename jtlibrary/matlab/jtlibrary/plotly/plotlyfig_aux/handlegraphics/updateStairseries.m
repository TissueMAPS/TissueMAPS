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
function obj = updateStairseries(obj, dataIndex)

%-store original stair handle-%
stair_group = obj.State.Plot(dataIndex).Handle; 

%------------------------------------------------------------------------%

%-get children-%
stair_child = get(stair_group ,'Children'); 

%------------------------------------------------------------------------%

%-update line -%
obj.State.Plot(dataIndex).Handle = stair_child(1); 
updateLineseries(obj,dataIndex); 

%------------------------------------------------------------------------%

%-revert handle-%
obj.State.Plot(dataIndex).Handle = stair_group;

end