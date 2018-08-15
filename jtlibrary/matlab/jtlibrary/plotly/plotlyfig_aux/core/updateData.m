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
%----UPDATE PLOT DATA/STYLE----%

function obj = updateData(obj, dataIndex)

%-update plot based on plot call class-%
try
    switch lower(obj.State.Plot(dataIndex).Class)
        
        %--CORE PLOT OBJECTS--%
        case 'image'
            updateImage(obj, dataIndex);
        case 'line'
            updateLineseries(obj, dataIndex);
        case 'patch'
            % check for histogram
            if isHistogram(obj,dataIndex)
                updateHistogram(obj,dataIndex);
            else
                updatePatch(obj, dataIndex);
            end
        case 'rectangle'
            updateRectangle(obj,dataIndex);
        case 'surface'
            updateSurfaceplot(obj,dataIndex);
            
            %-GROUP PLOT OBJECTS-%
        case 'area'
            updateArea(obj, dataIndex); 
        case 'areaseries'
            updateAreaseries(obj, dataIndex);
        case 'bar'
            updateBar(obj, dataIndex); 
        case 'barseries'
            updateBarseries(obj, dataIndex);
        case 'baseline'
            updateBaseline(obj, dataIndex);
        case {'contourgroup','contour'}
            updateContourgroup(obj,dataIndex);
        case 'errorbar'
            updateErrorbar(obj,dataIndex); 
        case 'errorbarseries'
            updateErrorbarseries(obj,dataIndex);
        case 'lineseries'
            updateLineseries(obj, dataIndex);
        case 'quiver'
            updateQuiver(obj, dataIndex); 
        case 'quivergroup'
            updateQuivergroup(obj, dataIndex);
        case 'scatter'
            updateScatter(obj, dataIndex); 
        case 'scattergroup'
            updateScattergroup(obj, dataIndex);
        case 'stair'
            updateStair(obj, dataIndex); 
        case 'stairseries'
            updateStairseries(obj, dataIndex);
        case 'stem'
            updateStem(obj, dataIndex); 
        case 'stemseries'
            updateStemseries(obj, dataIndex);
        case 'surfaceplot'
            updateSurfaceplot(obj,dataIndex);
            
            %--Plotly supported MATLAB group plot objects--%
        case {'hggroup','group'}
            % check for boxplot
            if isBoxplot(obj, dataIndex)
                updateBoxplot(obj, dataIndex);
            end
    end
    
catch exception
    if obj.UserData.Verbose
        fprintf([exception.message '\nWe had trouble parsing the ' obj.State.Plot(dataIndex).Class ' object.\n',...
                 'This trace might not render properly.\n\n']);
    end
end

%------------------------AXIS/DATA CLEAN UP-------------------------------%

%-AXIS INDEX-%
axIndex = obj.getAxisIndex(obj.State.Plot(dataIndex).AssociatedAxis);

%-CHECK FOR MULTIPLE AXES-%
[xsource, ysource] = findSourceAxis(obj,axIndex);

%-AXIS DATA-%
eval(['xaxis = obj.layout.xaxis' num2str(xsource) ';']);
eval(['yaxis = obj.layout.yaxis' num2str(ysource) ';']);

%-------------------------------------------------------------------------%

% check for xaxis dates
if strcmpi(xaxis.type, 'date')
    obj.data{dataIndex}.x =  convertDate(obj.data{dataIndex}.x);
end

% check for xaxis categories
if strcmpi(xaxis.type, 'category') && ...
        ~strcmp(obj.data{dataIndex}.type,'box')
    obj.data{dataIndex}.x =  get(obj.State.Plot(dataIndex).AssociatedAxis,'XTickLabel');
end

% check for yaxis dates
if strcmpi(yaxis.type, 'date')
    obj.data{dataIndex}.y =  convertDate(obj.data{dataIndex}.y);
end

% check for yaxis categories
if strcmpi(yaxis.type, 'category') && ...
        ~strcmp(obj.data{dataIndex}.type,'box')
    obj.data{dataIndex}.y =  get(obj.State.Plot(dataIndex).AssociatedAxis,'YTickLabel');
end

%-------------------------------------------------------------------------%

end