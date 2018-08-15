function PerimeterTrace = PerimeterAnalysis(LabelImage,WindowSize)
%PERIMETERANALYSIS calculate curvature of object perimeter
%
%   PERIMETERPROPS=PERIMETERANALYSIS(LABELIMAGE,WINDOW)
%   analyzes the perimeter of each object in LABELIMAGE to calculate
%   properties based on the curvature of the perimeter.
%
%   LABELIMAGE should be of kind as the output of bwlabel
%
%   WINDOW is the size of the sliding window used for calculating
%   derivatives. A sufficient size (eg 10) is necessary to smooth the
%   coordinate quantisation of pixel images.
%
%   PERIMETERPROPS is a cell array containing entries for each object in
%   LABELIMAGE. Each entry consists of a matrix with the number of rows
%   equaling the number of pixels at the perimeter of the object. The rows
%   therefore represent a continuous path around the object, starting at
%   the most left, top pixel of the object into direction right, bottom.
%   The collums of the entries represent the following quantities:
%       1,2: Pixel coordinates (row, column)
%       3,4: Normed inside normal vectors (row, column)
%       5,6: Curvature (row, column), not normed
%       7,8: Integer Curvature (row, column):
%            Componnets may only be -1, 0, 1, may therefore be used to
%            determine at which adjacent pixel the Curvature points.
%       9:   Norm of the Curvature
%       10:  Covex(+1), straight(0) or concave(-1)
%       11:  Convex, straight or concave region
%            (via weighted sliding WINDOW)
%       12,13: Tangential vector (row, column), not normed*
%
%   *Subject to change, check assignment of function return value (in code):
%   TangentialVectorsRaw contains not normed vectors,
%   TangentialVectors contains unit vecors (norm=1).
%
%   Additional information:
%   Given NormCurvature represents the norm of the curvature for pixels
%   contained in a convex or concave region (column 11 all +1 or -1):
%
%   sum(NormCurvature) sums up to 2*pi for a circle. This
%   does not apply to very small objects (pixel quantisation error). Care
%   must also be taken for large objects to pick a sufficiently large
%   window to accurately measure the curvature.
%   sum(NormCurvature) of a region divided by 2*pi therefore returns the
%   cirle fraction of the equivalent circle.
%
%   length(NormCurvature)/sum(NormCurvature); approximately returns the
%   equivalent radius of a circle with the same curvature as the region
%
%   Known issues/work to be done:
%   Objects with a perimeter smaller than half the window size cause errors.
%   It might be more meaningful to return non-unit tangential vectors?
%   Objects may not have long 1px wide 'antenna 'extensions. If such an
%   extension happens to be at the top left of the object and the starting
%   point is placed at the tip of the antenna, bwperimtrace may fail!
%   Applying
%       mindisk=getnhood(strel('disk',1,0));
%       imdilate(imerode(LabelImage,mindisk),mindisk);
%   before calling this function helps.
%
%   Author:
%     Anatol Schwab
%
%   (c) Pelkmans Lab 2012

ImSize=size(LabelImage);
ObjectIDs=setdiff(unique(LabelImage(:)),0);%just to make sure
NumObjects=length(ObjectIDs);
PerimeterTrace=cell(NumObjects,1);
ObjectProps=regionprops(LabelImage,'Extrema');%use extrema to find starting points on preimeter of Objects
%get ordered list of perimeter pixels for each object
for i=1:NumObjects
   CurrentObject=ObjectIDs(i);
   StartingPoint=ceil(ObjectProps(CurrentObject).Extrema(1,:));%use top left corner as starting point
   ObjectTrace=bwtraceboundary(LabelImage,fliplr(StartingPoint),'SE',8);%start towards right bottom corner, start=end ==>pixel twice in list! (convenient...)

   %calculate direction vector along perimeter
   %first calculate all inter pixel vectors

   %InterPixelVectors(i) contains vector from pixel with index i to pixel i+1
   InterPixelVectors=diff(ObjectTrace);%very convenient that the first entry also is the last!
   ObjectTrace=ObjectTrace(1:end-1,:);%remove last entry because it is the same as the first

   %normalize all vectors, maybe this can be written more efficiently in vectorized code
   for j=1:size(InterPixelVectors,1)
       InterPixelVectors(j,:)=InterPixelVectors(j,:)./norm(InterPixelVectors(j,:));
   end

   %pad the list of vector values so the window can be extracted conveniently
   BOffset=ceil(WindowSize/2)-1; %elements needed before i (subtract from i)
   AOffset=floor(WindowSize/2); %elements needed after i (add to i)
   PadInterPixelVectors=[InterPixelVectors(end-BOffset+1:end,:);InterPixelVectors;InterPixelVectors(1:AOffset,:)];
   TangentialVectors=zeros(size(InterPixelVectors,1),2,'double');%later filled with tangential unit vectors
   TangentialVectorsRaw=zeros(size(InterPixelVectors,1),2,'double');%not normed tangential vectors

   %apply sliding window to obtain tangential vectors
   for j=1:size(InterPixelVectors,1)
       Window=PadInterPixelVectors(j:j+WindowSize-1,:);
       CurrentVector=mean(Window);
       TangentialVectors(j,:)=CurrentVector/norm(CurrentVector);%tangential vectors are normalized!
       TangentialVectorsRaw(j,:)=CurrentVector;%save non normalized as well. may be integrated to give the object shape again?
   end

   %calculate normed normal vectors(always point towards the object/inward)
   NormalVectors=zeros(size(TangentialVectors,1),2,'double');
   for j=1:size(TangentialVectors,1)
       %there are two possible normal vectors, pick the one pointing
       %towards the object (there are better methods than checking both, but
       %doing so is very robust)
       NormA=[-TangentialVectors(j,2),TangentialVectors(j,1)];
       NormB=[TangentialVectors(j,2),-TangentialVectors(j,1)];
       %Make vectors minimal integer so they actually point at pixels (8
       %possible vectors), this allows to determine inside/outside
       IntNormA=round(NormA/max(abs(NormA)));
       IntNormB=round(NormB/max(abs(NormB)));
       %check the pixels the vectors point at
       TestPixelA=ObjectTrace(j,:)+IntNormA;
       TestPixelValueA=0;
       if min(TestPixelA)>=1&&min(ImSize-TestPixelA)>=0%rangecheck!
           TestPixelValueA=LabelImage(TestPixelA(1),TestPixelA(2))>0;
       end

       TestPixelB=ObjectTrace(j,:)+IntNormB;
       TestPixelValueB=0;
       if min(TestPixelB)>=1&&min(ImSize-TestPixelB)>=0%rangecheck!
           TestPixelValueB=LabelImage(TestPixelB(1),TestPixelB(2))>0;
       end
       %Check if test pixels were valid. If the pixel coordinates were not
       %valid the test value will remain zero. If the other pixel has
       %a valid and >0 value this pixel will be chosen.
       if xor(TestPixelValueA,TestPixelValueB)
           NormalVectors(j,:)=NormA*TestPixelValueA+NormB*TestPixelValueB;%only one of the test values is one!
       else
           NormalVectors(j,:)=[0,0];%error
       end
   end
   %append first element at end to get pseudo cyclic array
   TangentialVectorsCyclic=[TangentialVectors;TangentialVectors(1,:)];
   InterVectorCurvature=diff(TangentialVectorsCyclic);
   %pad for easy window extraction
   PadInterVectorCurvature=[InterVectorCurvature(end-BOffset+1:end,:);InterVectorCurvature;InterVectorCurvature(1:AOffset,:)];
   Curvature=zeros(size(TangentialVectors,1),2,'double');
   NormCurvature=zeros(size(TangentialVectors,1),1,'double');
   IntCurvature=zeros(size(TangentialVectors,1),2,'double');%integer vector for curvature, only contains 1,0,-1 values. 9 possible combinations
   ConvexConcave=zeros(size(TangentialVectors,1),1,'double');

   %apply sliding window to obtain curvature, calculate curvature
   %parameters
   for j=1:size(InterPixelVectors,1)
       Window=PadInterVectorCurvature(j:j+WindowSize-1,:);
       CurrentCurvature=mean(Window);
       Curvature(j,:)=CurrentCurvature;%/norm(CurrentVector);%norm or not???
       NormCurvature(j)=norm(CurrentCurvature);
       if sum(NormCurvature(j))~=0
          IntCurvature(j,:)=round(CurrentCurvature/max(abs(CurrentCurvature)));%scale so that the biggest component is one, then round
          TestPixel=ObjectTrace(j,:)+IntCurvature(j,:);%this pixel determines wether IntCurvature points away or towards the object
          if min(TestPixel)>=1&&min(ImSize-TestPixel)>=0%rangecheck!
              ConvexConcave(j)=-1+2*(LabelImage(TestPixel(1),TestPixel(2))>0);%gives +1(convex) or -1(concave)
          else
              ConvexConcave(j)=0;
          end
       else
          IntCurvature(j,:)=CurrentCurvature;% if the norm is zero, CurrentCurvature is zeros(dimensions,1). saves some calculations...
          ConvexConcave(j)=0;
       end
   end
   %calculate convex or concave regions by applying a sliding window to
   %convex/concave assignment for individual pixels.
   %Maybe weight values by curvature?
   PadConvexConcave=[ConvexConcave(end-BOffset+1:end,:);ConvexConcave;ConvexConcave(1:AOffset,:)];
   PadNormCurvature=[NormCurvature(end-BOffset+1:end,:);NormCurvature;NormCurvature(1:AOffset,:)];
   ConvexConcaveRegion=zeros(size(TangentialVectors,1),1,'double');
   for j=1:length(ConvexConcave)
       %ConvexConcaveRegion(j)=sign(mean(PadConvexConcave(j:j+WindowSize-1,:)));
       ConvexConcaveRegion(j)=sign(mean(PadConvexConcave(j:j+WindowSize-1,:).*PadNormCurvature(j:j+WindowSize-1,:)));
   end

   PerimeterTrace{i}=cat(2,ObjectTrace,NormalVectors,Curvature,IntCurvature,NormCurvature,ConvexConcave,ConvexConcaveRegion,TangentialVectorsRaw);%save perimeter pixel coordinates and tangential vector
end

end
