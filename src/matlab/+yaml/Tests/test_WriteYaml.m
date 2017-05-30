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
function stat = test_WriteYaml()

stat.ok = 1;
stat.desc = '';
try
    fprintf('Testing write ');
    stat.test_WY_Matrices = test_WY_Universal(PTH_PRIMITIVES(), 'matrices');
    fprintf('.');
    stat.test_WY_FloatingPoints = test_WY_Universal(PTH_PRIMITIVES(), 'floating_points');
    fprintf('.');
    stat.test_WY_Indentation = test_WY_Universal(PTH_PRIMITIVES(), 'indentation');
    fprintf('.');
    stat.test_WY_SequenceMapping = test_WY_Universal(PTH_PRIMITIVES(), 'sequence_mapping');
    fprintf('.');
    stat.test_WY_Simple = test_WY_Universal(PTH_PRIMITIVES(), 'simple');
    fprintf('.');
    stat.test_WY_Time = test_WY_Universal(PTH_PRIMITIVES(), 'time');
    fprintf('.');
    stat.test_WY_ComplexStructure = test_WY_Universal(PTH_IMPORT(), 'import');
    fprintf('.');
    stat.test_WY_usecase_01 = test_WY_Universal(PTH_PRIMITIVES(), 'usecase_struct_01');    
    fprintf('.\n');
catch    
    stat.ok = 0;
    stat.desc  = 'Program crash';
end

end

function result = PTH_PRIMITIVES()
    result = sprintf('Data%stest_primitives%s',filesep,filesep);
end

function result = PTH_IMPORT()
    result = sprintf('Data%stest_import%s',filesep,filesep);
end

function result = PTH_INHERITANCE()
    result = sprintf('Data%stest_inheritance%s',filesep,filesep);
end

function stat = test_WY_Universal(path, filename)
    stat.ok = 1;
    stat.desc = '';
    try
        data = load([path, filesep, filename, '.mat']);
        WriteYaml('~temporary.yaml',data.testval);
        ry = ReadYaml('~temporary.yaml');
        if ~isequalwithequalnans(ry, data.testval)
            stat.desc  = 'Wrong values loaded';
            stat.ok = 0;         
        end;
    catch
        stat.ok = 0;
        stat.desc = 'Crash';
    end;    
end