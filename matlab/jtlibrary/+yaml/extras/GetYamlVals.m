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
function [vals, timeaxis] = GetYamlVals(yamldata)
% this function converts data formatted in yaml style (cells containing timestamps and values) 
% into matlab user friendly matrices.

% obtain number of samples
n = max(size(yamldata));

if n
    if not(iscell(yamldata{1}))
        timeaxis = double(yamldata{1});
        vals   = cell2mat(yamldata(2:end));
    else

        % create output matrices
        timeaxis =  NaN*ones(n,1);
        if n % only if there are some elements of timeaxis
            vals = NaN*ones(n,numel(yamldata{1})-1);
        end
        for i=1:n
            timeaxis(i) = double(yamldata{i}{1});
            vals(i,:)   = cell2mat(yamldata{i}(2:end));
        end
    end

end

end % end of function

