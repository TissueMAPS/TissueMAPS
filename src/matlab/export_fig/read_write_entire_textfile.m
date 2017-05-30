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
%READ_WRITE_ENTIRE_TEXTFILE Read or write a whole text file to/from memory
%
% Read or write an entire text file to/from memory, without leaving the
% file open if an error occurs.
%
% Reading:
%   fstrm = read_write_entire_textfile(fname)
% Writing:
%   read_write_entire_textfile(fname, fstrm)
%
%IN:
%   fname - Pathname of text file to be read in.
%   fstrm - String to be written to the file, including carriage returns.
%
%OUT:
%   fstrm - String read from the file. If an fstrm input is given the
%           output is the same as that input. 

function fstrm = read_write_entire_textfile(fname, fstrm)
modes = {'rt', 'wt'};
writing = nargin > 1;
fh = fopen(fname, modes{1+writing});
if fh == -1
    error('Unable to open file %s.', fname);
end
try
    if writing
        fwrite(fh, fstrm, 'char*1');
    else
        fstrm = fread(fh, '*char')';
    end
catch ex
    fclose(fh);
    rethrow(ex);
end
fclose(fh);
end
