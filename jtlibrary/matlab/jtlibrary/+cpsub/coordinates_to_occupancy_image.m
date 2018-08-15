% Copyright 2018 Scott Berry, University of Zurich
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

function [occupancy_image] = coordinates_to_occupancy_image(coords, im_size)

    % discretize coordinates
    coords_int = round(coords);

    % count occurences at X Y positions
    [a, ~, b] = unique(coords_int(:,[1 2]), 'rows', 'stable');
    tally = accumarray(b, 1);
    xy_count = [a tally];

    % convert occurences to 2D image
    occupancy_image = zeros(im_size);
    linx_occurence = arrayfun(@(x,y) sub2ind(im_size,x,y), xy_count(:,2), xy_count(:,1));
    occupancy_image(linx_occurence) = xy_count(:,3);
end
