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
function y = generateBoxData(outliers, boxmin, Q2, med, Q3, boxmax)

%set number of data points
N = numel(outliers)*5+20;

%find percentile numbers
Q1Index = round(N*25/100);
Q2Index = round(N*50/100);
Q3Index = round(N*75/100);

outlierlow = outliers(outliers<med);
outlierhigh = outliers(outliers>med);

y=[outlierlow ...
    linspace(boxmin, Q2, Q1Index-numel(outlierlow)) ...
    linspace(Q2, med, Q2Index-Q1Index) ...
    linspace(med, Q3, Q3Index-Q2Index) ...
    linspace(Q3, boxmax, N-Q3Index-numel(outlierhigh)) ...
    outlierhigh];

end