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
function line = extractLineLine(line_data)

% EXTRACTS THE LINE STYLE USED FOR MATLAB OBJECTS
% OF TYPE "LINE". THESE OBJECTS ARE USED IN LINESERIES,
% STAIRSERIES, STEMSERIES, BASELINESERIES, AND BOXPLOTS

%-------------------------------------------------------------------------%

%-INITIALIZE OUTPUT-%
line = struct();

%-------------------------------------------------------------------------%

if(~strcmp(line_data.LineStyle,'none'))
    
    %-SCATTER LINE COLOR (STYLE)-%
    col = 255*line_data.Color;
    line.color = ['rgb(' num2str(col(1)) ',' num2str(col(2)) ',' num2str(col(3)) ')'];
    
    %---------------------------------------------------------------------%
    
    %-SCATTER LINE WIDTH (STYLE)-%
    line.width = line_data.LineWidth;
    
    %---------------------------------------------------------------------%
    
    %-SCATTER LINE DASH (STYLE)-%
    switch line_data.LineStyle
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
    
    %---------------------------------------------------------------------%
    
end
end