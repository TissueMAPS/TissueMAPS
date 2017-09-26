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
function result = merge_struct(p, s, donotmerge, deep)
import yaml.*;
if ~( isstruct(p) && isstruct(s) )
        error('Only structures can be merged.');
    end;
    if ~exist('donotmerge','var')
        donotmerge = {};
    end
    if ~exist('deep','var')
        deep = 0;
    elseif strcmp(deep, 'deep')
        deep = 1;
    end;
    result = p;
    for i = fields(s)'
        fld = char(i);
        if any(cellfun(@(x)isequal(x, fld), donotmerge))
            continue;
        end;
        if deep == 1 && isfield(result, fld) && isstruct(result.(fld)) && isstruct(s.(fld))
            result.(fld) = merge_struct(result.(fld), s.(fld), donotmerge, deep);
        else
            result.(fld) = s.(fld);
        end;
    end;
end
