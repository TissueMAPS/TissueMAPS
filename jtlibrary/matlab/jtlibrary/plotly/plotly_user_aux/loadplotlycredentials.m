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
function creds = loadplotlycredentials()

userhome = getuserdir();

plotly_credentials_file = fullfile(userhome,'.plotly','.credentials');

% check if credentials exist
if ~exist(plotly_credentials_file, 'file')
    error('Plotly:CredentialsNotFound',...
        ['It looks like you haven''t set up your plotly '...
        'account credentials yet.\nTo get started, save your '...
        'plotly username and API key by calling:\n'...
        '>>> saveplotlycredentials(username, api_key)\n\n'...
        'For more help, see https://plot.ly/MATLAB or contact '...
        'chris@plot.ly.']);
end

fileIDCred = fopen(plotly_credentials_file, 'r');

if(fileIDCred == -1)
    error('plotly:loadcredentials', ...
        ['There was an error reading your credentials file at '...
        plotly_credentials_file '. Contact chris@plot.ly for support.']);
end

creds_string_array = fread(fileIDCred, '*char');
creds_string = sprintf('%s',creds_string_array);
creds = loadjson(creds_string);

end
