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
function openurl(url)
try
    desktop = com.mathworks.mde.desk.MLDesktop.getInstance;
    editor = desktop.getGroupContainer('Editor');
    if(~isempty(url) && ~isempty(editor));
        fprintf(['\nLet''s have a look: <a href="matlab:web(''%s'', ''-browser'');">' url '</a>\n\n'], url)
    end
end
end