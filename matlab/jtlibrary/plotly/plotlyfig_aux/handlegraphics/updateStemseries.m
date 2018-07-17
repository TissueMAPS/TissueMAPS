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
function obj = updateStemseries(obj,dataIndex)

%-store original stem handle-%
stem_group = obj.State.Plot(dataIndex).Handle;

%-get children-%
stem_child = get(stem_group ,'Children');

%------------------------------------------------------------------------%

%-update line-%
obj.State.Plot(dataIndex).Handle = stem_child(1);
updateLineseries(obj,dataIndex);
stem_temp_data = obj.data{dataIndex};

%------------------------------------------------------------------------%

%-scatter mode-%
stem_temp_data.mode = 'lines+markers';

%------------------------------------------------------------------------%

%-update marker-%
obj.State.Plot(dataIndex).Handle = stem_child(2);
updateLineseries(obj,dataIndex);

%------------------------------------------------------------------------%

stem_temp_data.marker = obj.data{dataIndex}.marker;

%-hide every other marker-%
color_temp = cell(1,length(stem_temp_data.x));
line_color_temp = cell(1,length(stem_temp_data.x));

for n = 1:3:length(stem_temp_data.x)
    color_temp{n} = 'rgba(0,0,0,0)';
    color_temp{n+1} = stem_temp_data.marker.color;
    color_temp{n+2} = 'rgba(0,0,0,0)';
    line_color_temp{n} = 'rgba(0,0,0,0)';
    line_color_temp{n+1} = stem_temp_data.marker.line.color;
    line_color_temp{n+2} = 'rgba(0,0,0,0)';
end

% add new marker/line colors
stem_temp_data.marker.color = color_temp;
stem_temp_data.marker.line.color = line_color_temp;

%------------------------------------------------------------------------%

%-revert handle-%
obj.State.Plot(dataIndex).Handle = stem_group;
obj.data{dataIndex} = stem_temp_data;

end