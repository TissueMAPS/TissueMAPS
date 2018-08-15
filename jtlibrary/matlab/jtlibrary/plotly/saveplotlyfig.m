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
function p = saveplotlyfig(figure_or_data, filename, varargin)

%-----------------------------SAVEPLOTLYFIG-------------------------------%

% Save a MATLAB figure as a static image using Plotly

% [CALL]:

% p = saveplotlyfig(figure, filename)
% p = saveplotlyfig(data, filename)
% p = saveplotlyfig(figure, filename, varargin)
% p = saveplotlyfig(data, filename, varargin)

% [INPUTS]: [TYPE]{default} - description/'options'

% figure: [structure array]{} - structure with 'data' and 'layout' fields
% or
% figure: [plotlyfig object]{} - plotlyfig object with data and layout properties
% or
% figure: [figure handle]{} - figure handle
% data: [cell array]{} - cell array of Plotly traces
% varargin: [string]{.png} - image extension ('png','jpeg','pdf','svg')

% [OUTPUT]:

% static image save to the directory specified within the filename with the
% extension specified within filename or varargin.

% [EXAMPLE]:

% data.type = 'scatter';
% data.x = 1:10;
% data.y = 1:10;
% saveplotlyfig(data,'myimage.jpeg');

% [ADDITIONAL RESOURCES]:

% For full documentation and examples, see https://plot.ly/matlab/static-image-export/

%-------------------------------------------------------------------------%

%--PARSE FIGURE_OR_DATA--%
if iscell(figure_or_data)
    p = plotlyfig('Visible','off');
    p.data = figure_or_data;
    p.layout = struct(); 
    p.PlotOptions.Strip = false; 
elseif isstruct(figure_or_data);
    p = plotlyfig('Visible','off');
    p.data = figure_or_data.data;
    p.layout = figure_or_data.layout;
    p.PlotOptions.Strip = false; 
elseif isa(figure_or_data, 'plotlyfig')
    p = figure_or_data;
    p.PlotOptions.Strip = false;
elseif ishandle(figure_or_data)
    if strcmp(handle(figure_or_data).classhandle.name,'figure')
        p = plotlyfig(figure_or_data, 'strip', false);
    end
else
    errkey = 'plotlySaveImage:invalidInputs';
    error(errkey,plotlymsg(errkey));
end

%-------------------------------------------------------------------------%

%--MAKE CALL TO SAVEAS METHOD--%
p.saveas(filename, varargin{:});

%-------------------------------------------------------------------------%

end
