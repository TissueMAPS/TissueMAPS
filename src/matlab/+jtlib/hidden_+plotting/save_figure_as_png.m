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
function save_figure_as_png(fig, figure_file)
    % Write Matlab figure instance to file
    % (using the `export_fig <https://github.com/altmany/export_fig>`_ package).
    % 
    % Parameters
    % ----------
    % fig: matlab.ui.Figure
    %     figure instance
    % figure_file: char
    %     name of the figure file

    % export_fig requires the suffix to match the file type
    set(fig, 'PaperPosition', [0 0 5 5], 'PaperSize', [5 5]);
    figure_file = regexprep(figure_file, '\.\w+$', sprintf('.%s', 'png'));
    export_fig(fig, figure_file, '-transparent');

end
