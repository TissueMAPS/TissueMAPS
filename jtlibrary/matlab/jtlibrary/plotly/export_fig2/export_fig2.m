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
function export_fig2(fig, beautify, filename, format)

%----INPUT----% 
% fig: handle of figure to be converted
% beautify: binary flag 1 = use Plotly defaults, 0 = use MATLAB defaults
% fielname: name of file to be saved to specified directory
% format: one of 'png' (default), 'pdf', 'jpeg', 'svg'

%-------------------------------------------------------------------------%

%--CONSTRUCT PLOTLY FIGURE OBJECT--%
p = plotlyfig(fig, 'strip', beautify);

%-------------------------------------------------------------------------%

%----SAVE IMAGE-----%
saveplotlyfig(p, filename, format);

%-------------------------------------------------------------------------%

end