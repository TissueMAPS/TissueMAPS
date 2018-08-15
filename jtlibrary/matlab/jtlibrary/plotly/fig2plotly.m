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
function p = fig2plotly(varargin)

%------------------------------FIG2PLOTLY---------------------------------%

% Convert a MATLAB figure to a Plotly Figure

% [CALL]:

% p = fig2plotly
% p = fig2plotly(fig_han)
% p = fig2plotly(fig_han, 'property', value, ...)

% [INPUTS]: [TYPE]{default} - description/'options'

% fig_han: [handle]{gcf} - figure handle
% fig_struct: [structure array]{get(gcf)} - figure handle structure array

% [VALID PROPERTIES / VALUES]:

% filename: [string]{'untitled'} - filename as appears on Plotly
% fileopt: [string]{'new'} - 'new, overwrite, extend, append'
% world_readable: [boolean]{true} - public(true) / private(false)
% link: [boolean]{true} - show hyperlink (true) / no hyperlink (false)
% open: [boolean]{true} - open plot in browser (true)

% [OUTPUT]:

% p - plotlyfig object

% [ADDITIONAL RESOURCES]:

% For full documentation and examples, see https://plot.ly/matlab

%-------------------------------------------------------------------------%

%--FIGURE INITIALIZATION--%
if nargin == 0
    varargin{1} = gcf; 
end

%-------------------------------------------------------------------------%

%--CONSTRUCT PLOTLY FIGURE OBJECT--%
p = plotlyfig(varargin{:});

%-------------------------------------------------------------------------%

%--MAKE CALL TO PLOTLY--%
p.plotly; 

%-------------------------------------------------------------------------%

end
