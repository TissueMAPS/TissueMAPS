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
function datadump(data)
import yaml.*;
recurse(data, 0, []);
end
function result = recurse(data, level, addit)
import yaml.*;
indent = repmat(' | ',1,level);
    if iscell(data) && ~ismymatrix(data)
        result = iter_cell(data, level, addit);
    elseif isstruct(data)
        result = iter_struct(data, level, addit);
    else
        fprintf([indent,' +-Some data: ']);
        disp(data);
        result = data;
    end;
end
function result = iter_cell(data, level, addit)
import yaml.*;
indent = repmat(' | ',1,level);
    result = {};
    fprintf([indent,'cell {\n']);
    for i = 1:length(data)
        result{i} = recurse(data{i}, level + 1, addit);
    end;
    fprintf([indent,'} cell\n']);
end
function result = iter_struct(data, level, addit)
import yaml.*;
indent = repmat(' | ',1,level);
    result = struct();
    fprintf([indent,'struct {\n']);
    for i = fields(data)'
        fld = char(i);
        fprintf([indent,' +-field ',fld,':\n']);
        result.(fld) = recurse(data.(fld), level + 1, addit);
    end;
    fprintf([indent,'} struct\n']);
end
