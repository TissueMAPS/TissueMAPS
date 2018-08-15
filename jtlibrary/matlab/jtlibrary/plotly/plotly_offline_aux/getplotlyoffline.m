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
function getplotlyoffline(plotly_bundle_url)

    % download bundle 
    [plotly_bundle, extras] = urlread2(plotly_bundle_url, 'get');
   
    % handle response
    if ~extras.isGood
        error(['Whoops! There was an error attempting to ', ...
               'download the MATLAB offline Plotly ', ...
               'bundle. Status: %s %s.'], ...
               num2str(extras.status.value), extras.status.msg); 
    end

    % create Plotly config folder 
    userhome = getuserdir();
    plotly_config_folder = fullfile(userhome, '.plotly');
    [status, mess, messid] = mkdir(plotly_config_folder);
    validatedir(status, mess, messid, 'plotly'); 

    % create plotlyjs folder
    plotly_js_folder = fullfile(plotly_config_folder, 'plotlyjs');
    [status, mess, messid] = mkdir(plotly_js_folder);
    validatedir(status, mess, messid, 'plotlyjs');  

    % save bundle
    bundle = escapechars(plotly_bundle);
    bundle_name = 'plotly-matlab-offline-bundle.js'; 
    bundle_file = fullfile(plotly_js_folder, bundle_name); 
    file_id = fopen(bundle_file, 'w'); 
    fprintf(file_id, '%s', bundle);
    fclose(file_id); 
    
    % success! 
    fprintf(['\nSuccess! You can generate your first offline ', ...
             'graph\nusing the ''offline'' flag of fig2plotly as ', ...
             'follows:\n\n>> plot(1:10); fig2plotly(gcf, ', ... 
             '''offline'', true);\n\n'])
end
