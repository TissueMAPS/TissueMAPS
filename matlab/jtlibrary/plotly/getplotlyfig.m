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
function p = getplotlyfig(file_owner, file_id)

%-----------------------------SAVEPLOTLYFIG-------------------------------%

% Grab an online Plotly figure's data/layout information

% [CALL]:

% p = getplotlyfig(file_owner file_id)

% [INPUTS]: [TYPE]{default} - description/'options'

% file_owner: [string]{} - Unique Plotly username
% file_id [int]{} - the id of the graph you want to obtain

% [OUTPUT]:

% p - plotlyfig object

% [EXAMPLE]:

% url: https://plot.ly/~demos/1526
% fig = getplotlyfig('demos','1526'); 

% [ADDITIONAL RESOURCES]:

% For full documentation and examples, see https://plot.ly/matlab/get-requests/

%-------------------------------------------------------------------------%

%--CONSTRUCT PLOTLY FIGURE OBJECT--%
p = plotlyfig('Visible','off');

%-------------------------------------------------------------------------%

%--MAKE CALL TO DOWNLOAD METHOD--%
p.download(file_owner, file_id);

%-------------------------------------------------------------------------%

end
