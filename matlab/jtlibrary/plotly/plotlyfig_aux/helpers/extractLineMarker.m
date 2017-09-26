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
function marker = extractLineMarker(line_data)

% EXTRACTS THE MARKER STYLE USED FOR MATLAB OBJECTS 
% OF TYPE "LINE". THESE OBJECTS ARE USED IN LINESERIES, 
% STAIRSERIES, STEMSERIES, BASELINESERIES, AND BOXPLOTS

%-------------------------------------------------------------------------%

%-AXIS STRUCTURE-%
axis_data = get(ancestor(line_data.Parent,'axes'));

%-FIGURE STRUCTURE-%
figure_data = get(ancestor(line_data.Parent,'figure'));

%-INITIALIZE OUTPUT-%
marker = struct(); 

%-------------------------------------------------------------------------%

%-MARKER SIZE-%
marker.size = line_data.MarkerSize;

%-------------------------------------------------------------------------%

%-MARKER SYMBOL-%
if ~strcmp(line_data.Marker,'none')
    
    switch line_data.Marker
        case '.'
            marksymbol = 'circle';
        case 'o'
            marksymbol = 'circle';
        case 'x'
            marksymbol = 'x-thin-open';
        case '+'
            marksymbol = 'cross-thin-open';
        case '*'
            marksymbol = 'asterisk-open';
        case {'s','square'}
            marksymbol = 'square';
        case {'d','diamond'}
            marksymbol = 'diamond';
        case 'v'
            marksymbol = 'triangle-down';
        case '^'
            marksymbol = 'triangle-up';
        case '<'
            marksymbol = 'triangle-left';
        case '>'
            marksymbol = 'triangle-right';
        case {'p','pentagram'}
            marksymbol = 'star';
        case {'h','hexagram'}
            marksymbol = 'hexagram';
    end
    
    marker.symbol = marksymbol;
    
end

%-------------------------------------------------------------------------%

%-MARKER LINE WIDTH-%
marker.line.width = line_data.LineWidth;

%-------------------------------------------------------------------------%

filledMarkerSet = {'o','square','s','diamond','d',...
    'v','^', '<','>','hexagram','pentagram'};

filledMarker = ismember(line_data.Marker,filledMarkerSet);

%-------------------------------------------------------------------------%

%--MARKER FILL COLOR--%

MarkerColor = line_data.MarkerFaceColor;

if filledMarker
    if isnumeric(MarkerColor)
        col = 255*MarkerColor;
        markercolor = ['rgb(' num2str(col(1)) ',' num2str(col(2)) ',' num2str(col(3)) ')'];
    else
        switch MarkerColor
            case 'none'
                markercolor = 'rgba(0,0,0,0)';
            case 'auto'
                if ~strcmp(axis_data.Color,'none')
                    col = 255*axis_data.Color;
                    markercolor = ['rgb(' num2str(col(1)) ',' num2str(col(2)) ',' num2str(col(3)) ')'];
                else
                    col = 255*figure_data.Color;
                    markercolor = ['rgb(' num2str(col(1)) ',' num2str(col(2)) ',' num2str(col(3)) ')'];
                end
        end
    end
    
    marker.color = markercolor;
    
end

%-------------------------------------------------------------------------%

%-MARKER LINE COLOR-%

MarkerLineColor = line_data.MarkerEdgeColor;

if isnumeric(MarkerLineColor)
    col = 255*MarkerLineColor;
    markerlinecolor = ['rgb(' num2str(col(1)) ',' num2str(col(2)) ',' num2str(col(3)) ')'];
else
    switch MarkerLineColor
        case 'none'
            markerlinecolor = 'rgba(0,0,0,0)';
        case 'auto'
            col = 255*line_data.Color;
            markerlinecolor = ['rgb(' num2str(col(1)) ',' num2str(col(2)) ',' num2str(col(3)) ')'];
    end
end

if filledMarker
    marker.line.color = markerlinecolor;
else
    marker.color = markerlinecolor;
end

end