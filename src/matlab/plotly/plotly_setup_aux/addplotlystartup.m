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
function [warnings] = addplotlystartup(startupPaths)
%[1]looks at statup.m files specified by the entries of startupPaths
%[2]appends the addplotly function to startup.m files (if not already present)
%[3]checks for other plotly addpath calls within any startup.m and outputs warning

%output warnings
warnings = cell(size(startupPaths)); 

for locs = 1:size(startupPaths,1);
    %addpath string for Plotly API
    addString = 'addpath(genpath(fullfile(matlabroot,''toolbox'',''plotly'')),''-end'');';
    %open current startup.m to read
    currentStartupID = fopen(startupPaths{locs},'r');
    if currentStartupID == -1, error('plotly:startupRead',...
            ['\n\nShoot! It looks like something went wrong reading the file: ' ...
            '\n' startupPaths{locs} '\n' ... 
            '\nPlease contact your system admin. or chuck@plot.ly for more \ninformation. In the ' ...
            'mean time you can add the Plotly API \nto your search path manually whenever you need it! \n\n']);
    end
    %check for any instances of the addplotlyapi function
    startupScan = textscan(currentStartupID, '%s', 'delimiter', '\n', 'whitespace', '');
    startupLines = startupScan{1};
    Index = find(strcmp(startupLines,addString));
    otherPlotlyOccurrence = findstr(fileread(startupPaths{locs}),'plotly');
    %if addString is not in startup.m add it
    if(~any(Index));
        %reopen current startup.m with new permission
        currentStartupID = fopen(startupPaths{locs},'a+');
        if currentStartupID == -1, error('plotly:startupWrite',...
            ['\n\nShoot! It looks like something went wrong writing to the file: ' ...
            '\n\n' startupPaths{locs} '\n' ...
            '\nPlease contact your system admin. or chuck@plot.ly for more \ninformation. In the ' ...
            'mean time you can add the Plotly API \nto your search path manually whenever you need it! \n']);
        end
        fprintf(currentStartupID,['\n' addString]);
    end
    if(length(Index) ~= length(otherPlotlyOccurrence));
        warnings{locs} = ['\n[WARNING]: \n\nWe found an addpath specification for another version of Plotly at: ' ...
                                '\n\n' startupPaths{locs} '\n\nyou may be forcing MATLAB to look for an older version of Plotly!\n\n']; 
    else
        warnings{locs} = ''; 
    end
    fclose(currentStartupID);
end
end

