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
function s = TimeVals2Cell(time,datavalues,header)
% creates a typical struct with field named by header. Values are cell of
% date and vals.
% synopsis:
%  s = TimeVals2Cell(time,datavalues,header)
if ~iscell(header)
    header = {header};
end

for i=1:numel(header)
    s.(header{i}) = [num2cell(DateTime(time)) num2cell(datavalues(:,i))];
end
end