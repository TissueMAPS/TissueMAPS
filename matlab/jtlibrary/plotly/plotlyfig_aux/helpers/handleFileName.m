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
function handleFileName(obj)

%--IF EMPTY FILENAME, CHECK FOR PLOT TITLES--%
if isempty(obj.PlotOptions.FileName)
    for t = 1:obj.State.Figure.NumTexts
        if obj.State.Text(t).Title
            str = get(obj.State.Text(t).Handle,'String');
            interp = get(obj.State.Text(t).Handle,'Interpreter');
            obj.PlotOptions.FileName = parseString(str,interp);
        end
    end
end

%--IF FILENAME IS STILL EMPTY SET TO UNTITLED--%
if isempty(obj.PlotOptions.FileName)
    obj.PlotOptions.FileName = 'untitled';
end

end