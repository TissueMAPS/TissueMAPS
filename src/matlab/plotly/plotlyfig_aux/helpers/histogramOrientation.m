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
function orientation = histogramOrientation(hist_data)

%initialize output
orientation = [];

try
    %check to see if patch is in the shape of "vertical" rectangles :)
    if  size(hist_data.XData,1)==4  && size(hist_data.XData, 2) > 1 && ...
            all(hist_data.XData(1,:)==hist_data.XData(2,:)) && ...
            all(hist_data.XData(3,:)==hist_data.XData(4,:)) && ...
            all(hist_data.YData(1,:)==hist_data.YData(4,:)) && ...
            all(hist_data.YData(2,:)==hist_data.YData(3,:));
        orientation = 'v';
        %check to see if patch is in the shape of "horizontal" rectangles :)
    elseif size(hist_data.YData,1)==4 && size(hist_data.YData, 2) > 1 && ...
            all(hist_data.YData(1,:)==hist_data.YData(2,:)) && ...
            all(hist_data.YData(3,:)==hist_data.YData(4,:)) && ...
            all(hist_data.XData(1,:)==hist_data.XData(4,:)) && ...
            all(hist_data.XData(2,:)==hist_data.XData(3,:));
        orientation = 'h'; 
    end
end