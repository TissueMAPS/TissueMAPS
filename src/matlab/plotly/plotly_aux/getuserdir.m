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
function userDir = getuserdir
% GETUSERDIR  Retrieve the user directory
%   - Under Windows returns the %APPDATA% directory
%   - For other OSs uses java to retrieve the user.home directory

if ispc
    %     userDir = winqueryreg('HKEY_CURRENT_USER',...
    %         ['Software\Microsoft\Windows\CurrentVersion\' ...
    %          'Explorer\Shell Folders'],'Personal');
    userDir = getenv('appdata');
else
    userDir = char(java.lang.System.getProperty('user.home'));
end