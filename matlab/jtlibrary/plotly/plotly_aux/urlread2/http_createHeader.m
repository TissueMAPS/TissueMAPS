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
function header = http_createHeader(name,value)
%http_createHeader Simple function for creating input header to urlread2
%
%   header = http_createHeader(name,value)
%
%   CODE: header = struct('name',name,'value',value);
%
%   See Also: 
%       urlread2

header = struct('name',name,'value',value);