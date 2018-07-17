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
function face = extractAreaFace(area_data)

% EXTRACTS THE FACE STYLE USED FOR MATLAB OBJECTS
% OF TYPE "PATCH". THESE OBJECTS ARE USED IN AREASERIES
% BARSERIES, CONTOURGROUP, SCATTERGROUP.

%-------------------------------------------------------------------------%

%-AXIS STRUCTURE-%
axis_data = get(ancestor(area_data,'axes'));

%-FIGURE STRUCTURE-%
figure_data = get(ancestor(area_data,'figure'));

%-------------------------------------------------------------------------%

%-INITIALIZE OUTPUT-%
face = struct();

%-------------------------------------------------------------------------%

%--FACE FILL COLOR--%

%-figure colormap-%
colormap = figure_data.Colormap;

% face face color
MarkerColor = area_data.FaceColor;

if isnumeric(MarkerColor)
    col = 255*MarkerColor;
    facecolor = ['rgb(' num2str(col(1)) ',' num2str(col(2)) ',' num2str(col(3)) ')'];
else
    switch MarkerColor
        
        case 'none'
            
            facecolor = 'rgba(0,0,0,0)';
            
        case 'flat'
            areaACData = area_data.getColorAlphaDataExtents;
            capCD = max(min(areaACData(1,1),axis_data.CLim(2)),axis_data.CLim(1));
            scalefactor = (capCD - axis_data.CLim(1))/diff(axis_data.CLim);
            col =  255*(colormap(1 + floor(scalefactor*(length(colormap)-1)),:));
            facecolor = ['rgb(' num2str(col(1)) ',' num2str(col(2)) ',' num2str(col(3)) ')'];
    end
end

face.color = facecolor;

%-------------------------------------------------------------------------%

end