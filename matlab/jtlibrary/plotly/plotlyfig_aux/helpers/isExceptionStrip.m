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
function check = isExceptionStrip(grstruct, fieldname)

% initialize output
check = false;

% exception list {fieldname, val_types}
exceptions = {'color', @iscell, 'width', @(x)(length(x)>1), 'size', @(x)(length(x)>1)};

for e = 1:2:length(exceptions)
    
    %comparison function 
    compfun = exceptions{e+1};
    
    % look for fieldnames of type exceptions{e} and compare the underyling data using exceptions{e+1}
    if strcmp(fieldname, exceptions{e}) && compfun(grstruct.(fieldname))
        check = true;
    end
    
end
end