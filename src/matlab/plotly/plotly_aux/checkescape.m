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
function escaped_val = checkescape(val)
%adds '\' escape character if needed
ec = '\';
ind = find( (val == '"') | (val == '\' ) | (val == '/' ));
if(ind)
    if(ind(1) == 1)
        val = ['\' val];
        ind = ind + 1;
        ind(1) = [];
    end
    if (ind)
        val = [val ec(ones(1,length(ind)))]; %extend lengh of val to prep for char shifts.
        for i = 1:length(ind)
            val(ind(i):end) = [ec val(ind(i):end-1)];
            ind = ind+1;
        end
    end
end

escaped_val = val;