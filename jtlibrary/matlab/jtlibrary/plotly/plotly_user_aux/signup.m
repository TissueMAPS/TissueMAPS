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
function response = signup(username, email)
% SIGNUP(username, email)  Remote signup to plot.ly and plot.ly API
%     response = signup(username, email) makes an account on plotly and returns a temporary password and an api key
%
% See also plotly, plotlylayout, plotlystyle, signin
%
% For full documentation and examples, see https://plot.ly/api
    platform = 'MATLAB';
    payload = {'version', '0.2', 'un', username, 'email', email,'platform',platform};
    url = 'https://plot.ly/apimkacct';
    resp = urlread(url, 'Post', payload);
    response = loadjson(resp);

    f = fieldnames(response);
    if any(strcmp(f,'error'))
        error(response.error)
    end
    if any(strcmp(f,'warning'))
        fprintf(response.warning)
    end
    if any(strcmp(f,'message'))
        fprintf(response.message)
    end
    if any(strcmp(f,'filename'))
        plotlysession(response.filename)
    end

