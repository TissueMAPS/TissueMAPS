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
function marker = extractPatchFace(patch_data)
% EXTRACTS THE FACE STYLE USED FOR MATLAB OBJECTS
% OF TYPE "PATCH". THESE OBJECTS ARE USED BOXPLOTS.

%-------------------------------------------------------------------------%

%-AXIS STRUCTURE-%
axis_data = get(ancestor(patch_data.Parent,'axes'));

%-FIGURE STRUCTURE-%
figure_data = get(ancestor(patch_data.Parent,'figure'));

%-INITIALIZE OUTPUT-%
marker = struct(); 

%-------------------------------------------------------------------------%

%-PATCH EDGE WIDTH-%
marker.line.width = patch_data.LineWidth;

%-------------------------------------------------------------------------%

%-PATCH FACE COLOR-%

colormap = figure_data.Colormap;

if isnumeric(patch_data.FaceColor)
    
    %-paper_bgcolor-%
    col = 255*patch_data.FaceColor;
    marker.color = ['rgb(' num2str(col(1)) ',' num2str(col(2)) ',' num2str(col(3)) ')'];
    
else
    switch patch_data.FaceColor
        
        case 'none'
            marker.color = 'rgba(0,0,0,0)';
            
        case {'flat','interp'}
            
            switch patch_data.CDataMapping
                
                case 'scaled'
                    capCD = max(min(patch_data.FaceVertexCData(1,1),axis_data.CLim(2)),axis_data.CLim(1));
                    scalefactor = (capCD -axis_data.CLim(1))/diff(axis_data.CLim);
                    col =  255*(colormap(1+ floor(scalefactor*(length(colormap)-1)),:));
                case 'direct'
                    col =  255*(colormap(patch_data.FaceVertexCData(1,1),:));
                    
            end
            
            marker.color = ['rgb(' num2str(col(1)) ',' num2str(col(2)) ',' num2str(col(3)) ')'];
            
    end
end

%-------------------------------------------------------------------------%

%-PATCH EDGE COLOR-%

if isnumeric(patch_data.EdgeColor)
    
    col = 255*patch_data.EdgeColor;
    marker.line.color = ['rgb(' num2str(col(1)) ',' num2str(col(2)) ',' num2str(col(3)) ')'];
    
else
    switch patch_data.EdgeColor
        
        case 'none'
            marker.line.color = 'rgba(0,0,0,0,)';
            
        case 'flat'
            
            switch patch_data.CDataMapping
                
                case 'scaled'
                    capCD = max(min(patch_data.FaceVertexCData(1,1),axis_data.CLim(2)),axis_data.CLim(1));
                    scalefactor = (capCD -axis_data.CLim(1))/diff(axis_data.CLim);
                    col =  255*(colormap(1+floor(scalefactor*(length(colormap)-1)),:));
                    
                case 'direct'
                    col =  255*(colormap(patch_data.FaceVertexCData(1,1),:));
                    
            end
            
            marker.line.color = ['rgb(' num2str(col(1)) ',' num2str(col(2)) ',' num2str(col(3)) ')'];
    end
end
end
