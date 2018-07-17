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
function st = makecall(args, origin, structargs)

    % check if signed in and grab username, key, domain
    [un, key, domain] = signin;
    if isempty(un) || isempty(key)
        error('Plotly:CredentialsNotFound',...
             ['It looks like you haven''t set up your plotly '...
              'account credentials yet.\nTo get started, save your '...
              'plotly username and API key by calling:\n'...
              '>>> saveplotlycredentials(username, api_key)\n\n'...
              'For more help, see https://plot.ly/MATLAB or contact '...
              'chris@plot.ly.']);
    end

    platform = 'MATLAB';

    args = m2json(args);
    kwargs = m2json(structargs);
    url = [domain '/clientresp'];
    payload = {'platform', platform, 'version', plotly_version, 'args', args, 'un', un, 'key', key, 'origin', origin, 'kwargs', kwargs};

    if (is_octave)
        % use octave super_powers
        resp = urlread(url, 'post', payload);
    else
        % do it matlab way
        resp = urlread(url, 'Post', payload);
    end

    st = loadjson(resp);

    response_handler(resp);

end