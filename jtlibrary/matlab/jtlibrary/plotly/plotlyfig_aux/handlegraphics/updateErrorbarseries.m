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
function obj = updateErrorbarseries(obj, errorbarIndex)

% type: ...[DONE]
% symmetric: ...[DONE]
% array: ...[DONE]
% value: ...[NA]
% arrayminus: ...{DONE]
% valueminus: ...[NA]
% color: ...[DONE]
% thickness: ...[DONE]
% width: ...[DONE]
% opacity: ---[TODO]
% visible: ...[DONE]

%-------------------------------------------------------------------------%

%-ERRORBAR STRUCTURE-%
errorbar_data = get(obj.State.Plot(errorbarIndex).Handle);

%-ERRORBAR CHILDREN-%
errorbar_child = get(obj.State.Plot(errorbarIndex).Handle,'Children');

%-ERROR BAR LINE CHILD-%
errorbar_line_child_data = get(errorbar_child(2));

%-------------------------------------------------------------------------%

%-UPDATE LINESERIES-%
updateLineseries(obj, errorbarIndex);

%-------------------------------------------------------------------------%

%-errorbar visible-%
obj.data{errorbarIndex}.error_y.visible = true;

%-------------------------------------------------------------------------%

%-errorbar type-%
obj.data{errorbarIndex}.error_y.type = 'data';

%-------------------------------------------------------------------------%

%-errorbar symmetry-%
obj.data{errorbarIndex}.error_y.symmetric = false;

%-------------------------------------------------------------------------%

%-errorbar value-%
obj.data{errorbarIndex}.error_y.array = errorbar_data.UData;

%-------------------------------------------------------------------------%

%-errorbar valueminus-%
obj.data{errorbarIndex}.error_y.arrayminus = errorbar_data.LData;

%-------------------------------------------------------------------------%

%-errorbar thickness-%
obj.data{errorbarIndex}.error_y.thickness = errorbar_line_child_data.LineWidth;

%-------------------------------------------------------------------------%

%-errorbar width-%
obj.data{errorbarIndex}.error_y.width = obj.PlotlyDefaults.ErrorbarWidth;

%-------------------------------------------------------------------------%

%-errorbar color-%
col = 255*errorbar_line_child_data.Color;
obj.data{errorbarIndex}.error_y.color = ['rgb(' num2str(col(1)) ',' num2str(col(2)) ',' num2str(col(3)) ')'];

%-------------------------------------------------------------------------%

end