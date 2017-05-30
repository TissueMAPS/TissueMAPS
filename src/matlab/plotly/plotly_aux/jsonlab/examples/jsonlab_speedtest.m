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
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%         Benchmarking processing speed of savejson and loadjson
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

datalen=[1e3 1e4 1e5 1e6];
len=length(datalen);
tsave=zeros(len,1);
tload=zeros(len,1);
for i=1:len
    tic;
    json=savejson('data',struct('d1',rand(datalen(i),3),'d2',rand(datalen(i),3)>0.5));
    tsave(i)=toc;
    data=loadjson(json);
    tload(i)=toc-tsave(i);
    fprintf(1,'matrix size: %d\n',datalen(i));
end

loglog(datalen,tsave,'o-',datalen,tload,'r*-');
legend('savejson runtime (s)','loadjson runtime (s)');
xlabel('array size');
ylabel('running time (s)');
