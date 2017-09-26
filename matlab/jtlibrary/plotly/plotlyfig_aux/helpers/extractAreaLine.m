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
function line = extractAreaLine(area_data)

% EXTRACTS THE LINE STYLE USED FOR MATLAB OBJECTS
% OF TYPE "LINE". THESE OBJECTS ARE USED IN LINESERIES,
% STAIRSERIES, STEMSERIES, BASELINESERIES, AND BOXPLOTS

%-------------------------------------------------------------------------%

%-INITIALIZE OUTPUT-%
line = struct(); 

%-------------------------------------------------------------------------%

%-AREA LINE COLOR-%

if(~strcmp(area_data.LineStyle,'none'))
    
    % marker edge color
    LineColor = area_data.EdgeColor;
    
    if isnumeric(LineColor)
        col = 255*LineColor;
        linecolor = ['rgb(' num2str(col(1)) ',' num2str(col(2)) ',' num2str(col(3)) ')'];
    else
        linecolor = 'rgba(0,0,0,0)';
    end
    
    line.color = linecolor; 
    
%-------------------------------------------------------------------------%
    
    %-PATCH LINE WIDTH (STYLE)-%
    line.width = area_data.LineWidth;
    
%-------------------------------------------------------------------------%
    
    %-PATCH LINE DASH (STYLE)-%
    switch area_data.LineStyle
        case '-'
            LineStyle = 'solid';
        case '--'
            LineStyle = 'dash';
        case ':'
            LineStyle = 'dot';
        case '-.'
            LineStyle = 'dashdot';
    end
    
    line.dash = LineStyle;
    
%-------------------------------------------------------------------------%

end
end


