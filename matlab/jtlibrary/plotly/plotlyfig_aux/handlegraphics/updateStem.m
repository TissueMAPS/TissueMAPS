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
function obj = updateStem(obj,dataIndex)

%------------------------------------------------------------------------%

%-update line-%
updateLineseries(obj,dataIndex);
stem_temp_data = obj.data{dataIndex};

%------------------------------------------------------------------------%

%-scatter mode-%
stem_temp_data.mode = 'lines+markers';

%------------------------------------------------------------------------%

%-allocated space for extended data-%
xdata_extended = zeros(1,3*length(stem_temp_data.x)); 
ydata_extended = zeros(1,3*length(stem_temp_data.y));

%-format x data-%
m = 1; 
for n = 1:length(stem_temp_data.x)
    xdata_extended(m) = stem_temp_data.x(n); 
    xdata_extended(m+1) = stem_temp_data.x(n); 
    xdata_extended(m+2) = nan; 
    m = m + 3; 
end

%-format y data-%
m = 1; 
for n = 1:length(stem_temp_data.y)
    ydata_extended(m) = 0; 
    ydata_extended(m+1) = stem_temp_data.y(n); 
    ydata_extended(m+2) = nan; 
    m = m + 3; 
end

%-hide every other marker-%
color_temp = cell(1,3*length(stem_temp_data.y));
line_color_temp = cell(1,3*length(stem_temp_data.y));

for n = 1:3:length(color_temp)
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

stem_temp_data.x = xdata_extended; 
stem_temp_data.y = ydata_extended; 

%------------------------------------------------------------------------%

obj.data{dataIndex} = stem_temp_data;

end