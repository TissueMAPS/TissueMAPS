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
function result = doinheritance(r, tr)
import yaml.*;
if ~exist('tr','var')
        tr = r;
    end;
    result = recurse(r, 0, {tr});
end
function result = recurse(data, level, addit)
import yaml.*;
if iscell(data) && ~ismymatrix(data)
        result = iter_cell(data, level, addit);
    elseif isstruct(data)
        result = iter_struct(data, level, addit);
    else
        result = data;
    end;
end
function result = iter_cell(data, level, addit)
import yaml.*;
result = {};
    for i = 1:length(data)
        result{i} = recurse(data{i}, level + 1, addit);
    end;
    for i = 1:length(data)
        if isstruct(result{i}) && isfield(result{i}, kwd_parent())
            result{i} = inherit(result{i}, result{i}.(kwd_parent()), [], addit{1}, {}); % !!!
        end;
    end;
end
function result = iter_struct(data, level, addit)
import yaml.*;
result = data;
    for i = fields(data)'
        fld = char(i);
        result.(fld) = recurse(data.(fld), level + 1, addit);
    end;
    for i = fields(result)'
        fld = char(i);
        if isstruct(result.(fld)) && isfield(result.(fld), kwd_parent())
            result.(fld) = inherit(result.(fld), result.(fld).(kwd_parent()), [], addit{1}, {});
        end;
    end;
end
function result = inherit(child, parent_chr, container, oaroot, loc_imported)
import yaml.*;
result = child;
    if ~iscell(parent_chr)
        parent_chr = {parent_chr};
    end;
    for i = length(parent_chr):-1:1
        if contains(loc_imported, parent_chr{i})
            error('MATLAB:MATYAML:inheritedtwice',['Cyclic inheritance: ', parent_chr{i}]);
        end;
        try
            parentstruct = eval(['oaroot.',parent_chr{i}]);
        catch ex
            switch ex.identifier
                case {'MATLAB:nonExistentField', 'MATLAB:badsubscript'}
                    error('MATLAB:MATYAML:NonExistentParent', ['Parent was not found: ',parent_chr{i}]);
            end;
            rethrow(ex);
        end;
        if isstruct(parentstruct) && isfield(parentstruct, kwd_parent())
            next_loc_imported = loc_imported;
            next_loc_imported{end + 1} = parent_chr{i};
            result = merge_struct(inherit(parentstruct, parentstruct.(kwd_parent()), [], oaroot, next_loc_imported), result, {'import'});
        end;
        result = merge_struct(parentstruct, result, {'import'});
    end;
end
function result = contains(list, chr)
import yaml.*;
for i = 1:length(list)
        if strcmp(list{i}, chr)
            result = true;
            return;
        end;
    end;
    result = false;
end
