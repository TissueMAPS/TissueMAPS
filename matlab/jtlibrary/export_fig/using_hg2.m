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
%USING_HG2 Determine if the HG2 graphics engine is used
%
%   tf = using_hg2(fig)
%
%IN:
%   fig - handle to the figure in question.
%
%OUT:
%   tf - boolean indicating whether the HG2 graphics engine is being used
%        (true) or not (false).

% 19/06/2015 - Suppress warning in R2015b; cache result for improved performance

function tf = using_hg2(fig)
    persistent tf_cached
    if isempty(tf_cached)
        try
            if nargin < 1,  fig = figure('visible','off');  end
            oldWarn = warning('off','MATLAB:graphicsversion:GraphicsVersionRemoval');
            try
                % This generates a [supressed] warning in R2015b:
                tf = ~graphicsversion(fig, 'handlegraphics');
            catch
                tf = verLessThan('matlab','8.4');  % =R2014b
            end
            warning(oldWarn);
        catch
            tf = false;
        end
        if nargin < 1,  delete(fig);  end
        tf_cached = tf;
    else
        tf = tf_cached;
    end
end
