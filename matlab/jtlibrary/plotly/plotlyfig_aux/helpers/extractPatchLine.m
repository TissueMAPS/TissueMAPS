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
function line = extractPatchLine(patch_data)

% EXTRACTS THE LINE STYLE USED FOR MATLAB OBJECTS
% OF TYPE "LINE". THESE OBJECTS ARE USED IN LINESERIES,
% STAIRSERIES, STEMSERIES, BASELINESERIES, AND BOXPLOTS

%-------------------------------------------------------------------------%

%-AXIS STRUCTURE-%
axis_data = get(ancestor(patch_data.Parent,'axes'));

%-FIGURE STRUCTURE-%
figure_data = get(ancestor(patch_data.Parent,'figure'));

%-INITIALIZE OUTPUT-%
line = struct(); 

%-------------------------------------------------------------------------%

%-PATCH LINE COLOR-%

colormap = figure_data.Colormap;

if(~strcmp(patch_data.LineStyle,'none'))
    
    if isnumeric(patch_data.EdgeColor)
        
        col = 255*patch_data.EdgeColor;
        line.color = ['rgb(' num2str(col(1)) ',' num2str(col(2)) ',' num2str(col(3)) ')'];
        
    else
        switch patch_data.EdgeColor
            
            case 'none'
                line.color = 'rgba(0,0,0,0,)';
                
            case 'flat'
                
                switch patch_data.CDataMapping
                    
                    case 'scaled'
                        capCD = max(min(patch_data.FaceVertexCData(1,1),axis_data.CLim(2)),axis_data.CLim(1));
                        scalefactor = (capCD -axis_data.CLim(1))/diff(axis_data.CLim);
                        col =  255*(colormap(1+floor(scalefactor*(length(colormap)-1)),:));
                        
                    case 'direct'
                        col =  255*(colormap(patch_data.FaceVertexCData(1,1),:));
                        
                end
                
                line.color = ['rgb(' num2str(col(1)) ',' num2str(col(2)) ',' num2str(col(3)) ')'];
        end
    end
    
    %---------------------------------------------------------------------%
    
    %-PATCH LINE WIDTH (STYLE)-%
    line.width = patch_data.LineWidth;
    
    %---------------------------------------------------------------------%
    
    %-PATCH LINE DASH (STYLE)-%
    switch patch_data.LineStyle
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