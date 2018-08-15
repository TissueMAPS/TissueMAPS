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
function saveplotlycredentials(username, api_key, stream_ids)
% Save plotly authentication credentials.
% Plotly credentials are saved as JSON strings
% in ~/.plotly/.credentials

% catch missing input arguments
if nargin < 2
    error('plotly:savecredentials', ...
    ['Incorrect number of inputs. Please save your credentials ', ...
    'as follows: >> saveplotlycredentials(username, api_key,', ...
    '[optional]stream_ids)']); 
end

% if the credentials file exists, then load it up
try
    creds = loadplotlycredentials();
catch
    creds = struct();
end

% Create the .plotly folder
userhome = getuserdir();

plotly_credentials_folder   = fullfile(userhome,'.plotly');
plotly_credentials_file = fullfile(plotly_credentials_folder, '.credentials');

[status, mess, messid] = mkdir(plotly_credentials_folder);

if (status == 0)
    if(~strcmp(messid, 'MATLAB:MKDIR:DirectoryExists'))
        error('plotly:savecredentials',...
            ['Error saving credentials folder at ' ...
            plotly_credentials_folder ': '...
            mess ', ' messid '. Get in touch at ' ...
            'chris@plot.ly for support.']);
    end
end

fileIDCred = fopen(plotly_credentials_file, 'w');

if(fileIDCred == -1)
    error('plotly:savecredentials',...
        ['Error opening credentials file at '...
        plotly_credentials_file '. Get in touch at '...
        'chris@plot.ly for support.']);
end

switch nargin
    case 2
        creds.username = username;
        creds.api_key  = api_key;
    case 3
        creds.username = username;
        creds.api_key = api_key;
        creds.stream_ids = stream_ids;
end

creds_string = m2json(creds);

%write the json strings to the cred file
fprintf(fileIDCred,'%s',creds_string);
fclose(fileIDCred);

%signin using newly saved credentials
signin(username, api_key);

end
