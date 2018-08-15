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
%----UPDATE FIGURE DATA/LAYOUT----%

function obj = updateFigure(obj)

%--------PLOTLY LAYOUT FIELDS---------%

% title ..........[HANDLED BY updateAxis]
% titlefont ..........[HANDLED BY updateAxis]
% font ..........[HANDLED BY updateAxis]
% showlegend ..........[HANDLED BY updateAxis]
% autosize ... DONE
% width ... DONE
% height .... DONE
% xaxis ..........[HANDLED BY updateAxis]
% yaxis ..........[HANDLED BY updateAxis]
% legend ..........[HANDLED BY updateAxis]
% annotations ..........[HANDLED BY updateAnnotation]
% margin ...DONE
% paper_bgcolor ...DONE
% plot_bgcolor ..........[HANDLED BY updateAxis]
% hovermode ..........[NOT SUPPORTED IN MATLAB]
% dragmode ..........[NOT SUPPORTED IN MATLAB]
% separators ..........[NOT SUPPORTED IN MATLAB]
% barmode ..........[HANDLED BY updateBar]
% bargap ..........[HANDLED BY updateBar]
% bargroupgap ..........[HANDLED BY updateBar]
% boxmode ..........[HANDLED BY updateBox]
% radialaxis ..........[HANDLED BY updatePolar]
% angularaxis ..........[HANDLED BY updatePolar]
% direction ..........[HANDLED BY updatePolar]
% orientation ..........[HANDLED BY updatePolar]
% hidesources ..........[NOT SUPPORTED IN MATLAB]


%-STANDARDIZE UNITS-%
figunits = get(obj.State.Figure.Handle,'Units');
set(obj.State.Figure.Handle,'Units','pixels');

%-FIGURE DATA-%
figure_data = get(obj.State.Figure.Handle);

%-------------------------------------------------------------------------%

%-figure autosize-%
obj.layout.autosize = false;

%-------------------------------------------------------------------------%

%-figure margin pad-%
obj.layout.margin.pad = obj.PlotlyDefaults.MarginPad;

%-------------------------------------------------------------------------%

%-figure show legend-%
if(obj.State.Figure.NumLegends > 1)
    obj.layout.showlegend = true;
else
    obj.layout.showlegend = false;
end

%-------------------------------------------------------------------------%

%-margins-%
obj.layout.margin.l = 0;
obj.layout.margin.r = 0;
obj.layout.margin.b = 0;
obj.layout.margin.t = 0;

%-------------------------------------------------------------------------%

%-figure width-%
obj.layout.width = figure_data.Position(3)*obj.PlotlyDefaults.FigureIncreaseFactor;

%-------------------------------------------------------------------------%

%-figure height-%
obj.layout.height = figure_data.Position(4)*obj.PlotlyDefaults.FigureIncreaseFactor;

%-------------------------------------------------------------------------%

%-figure paper bgcolor-%
col = 255*figure_data.Color;
obj.layout.paper_bgcolor = ['rgb(' num2str(col(1)) ',' num2str(col(2)) ',' num2str(col(3)) ')'];

%-------------------------------------------------------------------------%

%-figure hovermode-%
obj.layout.hovermode = 'closest';

%-------------------------------------------------------------------------%

%-REVERT UNITS-%
set(obj.State.Figure.Handle,'Units',figunits);

end


