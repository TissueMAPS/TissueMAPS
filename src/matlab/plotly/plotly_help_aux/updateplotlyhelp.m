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
%----UPDATE THE PLOTLY HELP GRAPH REFERENCE----%
function updateplotlyhelp

% remote Plotly Graph Reference url
remote = ['https://raw.githubusercontent.com/plotly/',...
    'graph_reference/master/graph_objs/matlab/graph_objs_keymeta.json'];

% download the remote content
try
    prContent = urlread(remote);
catch
    fprintf(['\nAn error occurred while trying to read the latest\n',...
        'Plotly MATLAB API graph reference from:\n',...
        'https://github.com/plotly/graph_reference.\n']);
    return
end

% load the json into a struct
pr = loadjson(prContent); 

%------------------------MATLAB SPECIFIC TWEAKS---------------------------%

%-key_type changes-%
pr.annotation.xref.key_type = 'plot_info'; 
pr.annotation.yref.key_type = 'plot_info'; 
pr.line.shape.key_type = 'plot_info'; 

%-------------------------------------------------------------------------%

% save directory
helpdir = fullfile(fileparts(which('updateplotlyhelp')),'plotly_reference'); 

% pr filename 
prname = fullfile(helpdir); 

%----save----%
save(prname,'pr'); 

end