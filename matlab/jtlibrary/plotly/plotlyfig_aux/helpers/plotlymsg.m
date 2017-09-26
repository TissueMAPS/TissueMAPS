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
function errormsg = plotlymsg(key)
switch key
    %--plotlyfig constructor--%
    case 'plotlyfigConstructor:notSignedIn'
        errormsg = '\nOops! You must be signed in to initialize a plotlyfig object.\n'; 
    case 'plotlyfigConstructor:invalidInputs'
        errormsg = ['\nOops! It appears that you did not initialize the plotlyfig object using the\n', ...
            'required: >>  plotlyfig(handle [optional],''property'',''value'',...) \n',...
            'input structure. Please try again or contact chuck@plot.ly for any additional help!\n\n'];
        %--saveplotlyfig invocation--%;
    case 'plotlySaveImage:invalidInputs'
        errormsg = ['\nOops! It appears that you did not invoke the saveplotlyfig function using the\n', ...
            'required: >>  saveplotlyfig(plotly_figure, ...) input structure, where plotly_figure\n',...
            'is of type cell (for data traces) or of type struct (with data and layout fields). \n',...
            'Please try again or contact chuck@plot.ly for any additional help!\n\n'];
        
end
end
