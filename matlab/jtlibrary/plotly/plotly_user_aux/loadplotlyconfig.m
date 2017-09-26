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
function config = loadplotlyconfig()

userhome = getuserdir();

plotly_config_file = fullfile(userhome,'.plotly','.config');

% check if config exist
if ~exist(plotly_config_file, 'file')
    error('Plotly:ConfigNotFound',...
        ['It looks like you haven''t set up your plotly '...
        'account configuration file yet.\nTo get started, save your '...
        'plotly/stream endpoint domain by calling:\n'...
        '>>> saveplotlycredentials(plotly_domain, plotly_streaming_domain)\n\n'...
        'For more help, see https://plot.ly/MATLAB or contact '...
        'chris@plot.ly.']);
end

fileIDConfig = fopen(plotly_config_file, 'r');

if(fileIDConfig == -1)
    error('plotly:loadconfig', ...
        ['There was an error reading your configuration file at '...
        plotly_credentials_file '. Contact chris@plot.ly for support.']);
end

config_string_array = fread(fileIDConfig, '*char');
config_string = sprintf('%s',config_string_array);
config = loadjson(config_string);

end
