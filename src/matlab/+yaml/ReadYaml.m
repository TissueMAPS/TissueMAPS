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
function result = ReadYaml(filename, nosuchfileaction, makeords, treatasdata, dictionary)
import yaml.*;
if ~exist('nosuchfileaction','var')
        nosuchfileaction = 0;
    end;
    if ~ismember(nosuchfileaction,[0,1])
        error('nosuchfileexception parameter must be 0,1 or missing.');
    end;
    if ~exist('makeords','var')
        makeords = 0;
    end;
    if ~ismember(makeords,[0,1])
        error('makeords parameter must be 0,1 or missing.');
    end;    
    if(~exist('treatasdata','var'))
        treatasdata = 0;
    end;
    if ~ismember(treatasdata,[0,1])
        error('treatasdata parameter must be 0,1 or missing.');
    end; 
    ry = ReadYamlRaw(filename, 0, nosuchfileaction, treatasdata);
    ry = deflateimports(ry);
    if iscell(ry) &&         length(ry) == 1 &&         isstruct(ry{1}) &&         length(fields(ry{1})) == 1 &&         isfield(ry{1},'import')        
        ry = ry{1};
    end;
    ry = mergeimports(ry);    
    ry = doinheritance(ry);
    ry = makematrices(ry, makeords);    
    if exist('dictionary','var')
        ry = dosubstitution(ry, dictionary);
    end;
    result = ry;
    clear global nsfe;
end
