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
function Threshold = calculateThresholdLevel(ThresholdMethod,pObject,MinimumThreshold,MaximumThreshold,ThresholdCorrection,OrigImage,MaskImage)

if ~isempty(MaskImage)
    if size(MaskImage)==size(OrigImage)
        MaskImage = logical(MaskImage);
        LinearMaskedImage = OrigImage(MaskImage~=0);
    else
        error('The provided Mask Image has an invalid size.')
    end
else
    LinearMaskedImage = OrigImage(:);
end

if ~isempty(strfind(ThresholdMethod,'Global'))
    MethodFlag = 0;
elseif ~isempty(strfind(ThresholdMethod,'Adaptive'))
    MethodFlag = 1;
elseif ~isempty(strfind(ThresholdMethod,'PerObject'))
    MethodFlag = 2;
else
    error('The Threshold method must be specified with ''Global'', ''Adaptive'' or ''PerObject''.')
end
%%% Chooses the first word of the method name (removing 'Global' or 'Adaptive' or 'PerObject').
ThresholdMethod = strtok(ThresholdMethod);
%%% Makes sure we are using an existing thresholding method.
if isempty(strmatch(ThresholdMethod,{'Otsu','MoG','Background','RobustBackground','RidlerCalvard'},'exact'))
    error(['The method chosen for thresholding, ',ThresholdMethod,', was not recognized.'])
end

%%% For all methods, Global or Adaptive or PerObject, we want to
%%% calculate the global threshold. Sends the linear masked image to
%%% the appropriate thresholding subfunction.
eval(['Threshold = ',ThresholdMethod,'(LinearMaskedImage,pObject);']);
%%% This evaluates to something like: Threshold =
%%% Otsu(LinearMaskedImage,pObject);

%%% The global threshold is used to constrain the Adaptive or PerObject
%%% thresholds.
GlobalThreshold = Threshold;

%%% For Global, we are done. There are more steps involved for Adaptive
%%% and PerObject methods.

if MethodFlag == 1 %%% The Adaptive method.
    %%% Choose the block size that best covers the original image in
    %%% the sense that the number of extra rows and columns is minimal.
    %%% Get size of image
    [m,n] = size(OrigImage);
    %%% Deduce a suitable block size based on the image size and the
    %%% percentage of image covered by objects. We want blocks to be
    %%% big enough to contain both background and objects. The more
    %%% uneven the ratio between background pixels and object pixels
    %%% the larger the block size need to be. The minimum block size is
    %%% about 50x50 pixels. The line below divides the image in 10x10
    %%% blocks, and makes sure that the block size is at least 50x50
    %%% pixels.
    BlockSize = max(50,min(round(m/10),round(n/10)));
    %%% Calculates a range of acceptable block sizes as plus-minus 10%
    %%% of the suggested block size.
    BlockSizeRange = floor(1.1*BlockSize):-1:ceil(0.9*BlockSize);
    [ignore,index] = min(ceil(m./BlockSizeRange).*BlockSizeRange-m + ceil(n./BlockSizeRange).*BlockSizeRange-n); %#ok Ignore MLint
    BestBlockSize = BlockSizeRange(index);
    %%% Pads the image so that the blocks fit properly.
    RowsToAdd = BestBlockSize*ceil(m/BestBlockSize) - m;
    ColumnsToAdd = BestBlockSize*ceil(n/BestBlockSize) - n;
    RowsToAddPre = round(RowsToAdd/2);
    RowsToAddPost = RowsToAdd - RowsToAddPre;
    ColumnsToAddPre = round(ColumnsToAdd/2);
    ColumnsToAddPost = ColumnsToAdd - ColumnsToAddPre;
    PaddedImage = padarray(OrigImage,[RowsToAddPre ColumnsToAddPre],'replicate','pre');
    PaddedImage = padarray(PaddedImage,[RowsToAddPost ColumnsToAddPost],'replicate','post');
    PaddedImageandCropMask = PaddedImage;
    if exist('MaskImage','var')
        %%% Pad the crop mask too.
        PaddedCropMask = padarray(MaskImage,[RowsToAddPre ColumnsToAddPre],'replicate','pre');
        PaddedCropMask = padarray(PaddedCropMask,[RowsToAddPost ColumnsToAddPost],'replicate','post');
        %%% For the CPblkproc function, the original image and the crop
        %%% mask image (if it exists) must be combined into one.
        PaddedImageandCropMask(:,:,2) = PaddedCropMask;
        %%% And the Block must have two layers, too.
        Block = [BestBlockSize BestBlockSize 2];
        %%% Sends the linear masked image to the appropriate
        %%% thresholding subfunction, in blocks.
        eval(['Threshold = CPblkproc(PaddedImageandCropMask,Block,@',ThresholdMethod,',pObject);']);
        %%% This evaluates to something like: Threshold =
        %%% CPblkproc(PaddedImageandCropMask,Block,@Otsu,handles,ImageN
        %%% ame);
    else
        %%% If there is no crop mask, then we can simply use the
        %%% blkproc function rather than CPblkproc.
        Block = [BestBlockSize BestBlockSize];
        eval(['Threshold = blkproc(PaddedImageandCropMask,Block,@',ThresholdMethod,',pObject);']);
    end
    
    %%% Resizes the block-produced image to be the size of the padded
    %%% image. Bilinear prevents dipping below zero. The crop the image
    %%% get rid of the padding, to make the result the same size as the
    %%% original image.
    Threshold = imresize(Threshold, size(PaddedImage), 'bilinear');
    Threshold = Threshold(RowsToAddPre+1:end-RowsToAddPost,ColumnsToAddPre+1:end-ColumnsToAddPost);
    
elseif MethodFlag == 2 %%% The PerObject method.
    %%% This method require the Retrieved CropMask, which should be a
    %%% label matrix of objects, where each object consists of an
    %%% integer that is its label.
    if ~exist('RetrievedCropMask','var')
        error('You have chosen to calculate the threshold on a per-object basis, but the image of the objects you want to use could not be found.')
    end
    %%% Initializes the Threshold variable (which will end up being the
    %%% same size as the original image).
    Threshold = ones(size(OrigImage));
    NumberOfLabelsInLabelMatrix = max(RetrievedCropMask(:));
    for i = 1:NumberOfLabelsInLabelMatrix
        %%% Chooses out the pixels in the orig image that correspond
        %%% with i in the label matrix. This simultaneously produces a
        %%% linear set of numbers (and masking of pixels outside the
        %%% object is done automatically, in a sense).
        Intensities = OrigImage(RetrievedCropMask == i);
        
        %%% Sends those pixels to the appropriate threshold
        %%% subfunctions.
        eval(['CalculatedThreshold = ',ThresholdMethod,'(Intensities,pObject);']);
        %%% This evaluates to something like: Threshold =
        %%% Otsu(Intensities);
        
        %%% Sets the pixels corresponding to object i to equal the
        %%% calculated threshold.
        Threshold(RetrievedCropMask == i) = CalculatedThreshold;
        %            figure(32), imagesc(Threshold), colormap('gray')
    end
end

if MethodFlag == 1 || MethodFlag == 2 %%% For the Adaptive and the PerObject methods.
    %%% Adjusts any of the threshold values that are significantly
    %%% lower or higher than the global threshold.  Thus, if there are
    %%% no objects within a block (e.g. if cells are very sparse), an
    %%% unreasonable threshold will be overridden.
    Threshold(Threshold <= 0.7*GlobalThreshold) = 0.7*GlobalThreshold;
    Threshold(Threshold >= 1.5*GlobalThreshold) = 1.5*GlobalThreshold;
end


%%% Correct the threshold using the correction factor given by the user and
%%% make sure that the threshold is not larger than the minimum threshold
Threshold = ThresholdCorrection*Threshold;
Threshold = max(Threshold,MinimumThreshold);
Threshold = min(Threshold,MaximumThreshold);


end








%%%%%%%%%%%%%%%%%%%%
%%% SUBFUNCTIONS %%%
%%%%%%%%%%%%%%%%%%%%

function level = Otsu(im,pObject)
%%% This is the Otsu method of thresholding, adapted from MATLAB's
%%% graythresh function. Our modifications work in log space, and take into
%%% account the max and min values in the image.

%%% The following is needed for the adaptive cases where there the image
%%% has been cropped. This must be done within this subfunction, rather
%%% than in the main code prior to sending to this function via blkproc,
%%% because the blkproc function takes a single image as input, so we have
%%% to store the image and its cropmask in a single image variable.
if ndims(im) == 3
    Image = im(:,:,1);
    CropMask = im(:,:,2);
    clear im
    im = Image(CropMask==1);
else
    im = im(:);
end

if max(im) == min(im)
    level = im(1);
elseif isempty(im)
    %%% im will be empty if the entire image is cropped away by the
    %%% CropMask. I am not sure whether it is better to then set the level
    %%% to 0 or 1. Setting the level to empty causes problems downstream.
    %%% Presumably setting the level to 1 will not cause major problems
    %%% because the other blocks will average it out as we get closer to
    %%% real objects?
    level = 1;
else
    %%% We want to limit the dynamic range of the image to 256. Otherwise,
    %%% an image with almost all values near zero can give a bad result.
    minval = max(im)/256;
    im(im < minval) = minval;
    im = log(im);
    minval = min (im);
    maxval = max (im);
    im = (im - minval) / (maxval - minval);
    level = exp(minval + (maxval - minval) * graythresh(im));
end

end


function level = MoG(im,pObject)
%%% Stands for Mixture of Gaussians. This function finds a suitable
%%% threshold for the input image Block. It assumes that the pixels in the
%%% image belong to either a background class or an object class. 'pObject'
%%% is an initial guess of the prior probability of an object pixel, or
%%% equivalently, the fraction of the image that is covered by objects.
%%% Essentially, there are two steps. First, a number of Gaussian
%%% distributions are estimated to match the distribution of pixel
%%% intensities in OrigImage. Currently 3 Gaussian distributions are
%%% fitted, one corresponding to a background class, one corresponding to
%%% an object class, and one distribution for an intermediate class. The
%%% distributions are fitted using the Expectation-Maximization (EM)
%%% algorithm, a procedure referred to as Mixture of Gaussians modeling.
%%% When the 3 Gaussian distributions have been fitted, it's decided
%%% whether the intermediate class models background pixels or object
%%% pixels based on the probability of an object pixel 'pObject' given by
%%% the user.

%%% The following is needed for the adaptive cases where there the image
%%% has been cropped. This must be done within this subfunction, rather
%%% than in the main code prior to sending to this function via blkproc,
%%% because the blkproc function takes a single image as input, so we have
%%% to store the image and its cropmask in a single image variable.
if ndims(im) == 3
    Image = im(:,:,1);
    CropMask = im(:,:,2);
    clear im
    im = Image(CropMask==1);
else im = im(:);
end

if max(im) == min(im)
    level = im(1);
elseif isempty(im)
    %%% im will be empty if the entire image is cropped away by the
    %%% CropMask. I am not sure whether it is better to then set the level
    %%% to 0 or 1. Setting the level to empty causes problems downstream.
    %%% Presumably setting the level to 1 will not cause major problems
    %%% because the other blocks will average it out as we get closer to
    %%% real objects?
    level = 1;
else
    
    %%% The number of classes is set to 3
    NumberOfClasses = 3;
    
    %%% If the image is larger than 512x512, select a subset of 512^2
    %%% pixels for speed. This should be enough to capture the statistics
    %%% in the image.
    % im = im(:);
    if length(im) > 512^2
        indexes = randperm(length(im));
        im = im(indexes(1:512^2));
    end
    
    %%% Convert user-specified percentage of image covered by objects to a
    %%% prior probability of a pixel being part of an object.
    pObject = str2double(pObject(1:2))/100;
    %%% Get the probability for a background pixel
    pBackground = 1 - pObject;
    
    %%% Initialize mean and standard deviations of the three Gaussian
    %%% distributions by looking at the pixel intensities in the original
    %%% image and by considering the percentage of the image that is
    %%% covered by object pixels. Class 1 is the background class and Class
    %%% 3 is the object class. Class 2 is an intermediate class and we will
    %%% decide later if it encodes background or object pixels. Also, for
    %%% robustness the we remove 1% of the smallest and highest intensities
    %%% in case there are any quantization effects that have resulted in
    %%% unaturally many 0:s or 1:s in the image.
    im = sort(im);
    im = im(ceil(length(im)*0.01):round(length(im)*0.99));
    ClassMean(1) = im(round(length(im)*pBackground/2));                      %%% Initialize background class
    ClassMean(3) = im(round(length(im)*(1 - pObject/2)));                    %%% Initialize object class
    ClassMean(2) = (ClassMean(1) + ClassMean(3))/2;                                            %%% Initialize intermediate class
    %%% Initialize standard deviations of the Gaussians. They should be the
    %%% same to avoid problems.
    ClassStd(1:3) = 0.15;
    %%% Initialize prior probabilities of a pixel belonging to each class.
    %%% The intermediate class is gets some probability from the background
    %%% and object classes.
    pClass(1) = 3/4*pBackground;
    pClass(2) = 1/4*pBackground + 1/4*pObject;
    pClass(3) = 3/4*pObject;
    
    %%% Apply transformation.  a < x < b, transform to log((x-a)/(b-x)).
    %a = - 0.000001; b = 1.000001; im = log((im-a)./(b-im)); ClassMean =
    %log((ClassMean-a)./(b - ClassMean)) ClassStd(1:3) = [1 1 1];
    
    %%% Expectation-Maximization algorithm for fitting the three Gaussian
    %%% distributions/classes to the data. Note, the code below is general
    %%% and works for any number of classes. Iterate until parameters don't
    %%% change anymore.
    delta = 1;
    while delta > 0.001
        %%% Store old parameter values to monitor change
        oldClassMean = ClassMean;
        
        %%% Update probabilities of a pixel belonging to the background or
        %%% object1 or object2
        for k = 1:NumberOfClasses
            pPixelClass(:,k) = pClass(k)* 1/sqrt(2*pi*ClassStd(k)^2) * exp(-(im - ClassMean(k)).^2/(2*ClassStd(k)^2));
        end
        pPixelClass = pPixelClass ./ repmat(sum(pPixelClass,2) + eps,[1 NumberOfClasses]);
        
        %%% Update parameters in Gaussian distributions
        for k = 1:NumberOfClasses
            pClass(k) = mean(pPixelClass(:,k));
            ClassMean(k) = sum(pPixelClass(:,k).*im)/(length(im)*pClass(k));
            ClassStd(k)  = sqrt(sum(pPixelClass(:,k).*(im - ClassMean(k)).^2)/(length(im)*pClass(k))) + sqrt(eps);    % Add sqrt(eps) to avoid division by zero
        end
        
        %%% Calculate change
        delta = sum(abs(ClassMean - oldClassMean));
    end
    
    %%% Now the Gaussian distributions are fitted and we can describe the
    %%% histogram of the pixel intensities as the sum of these Gaussian
    %%% distributions. To find a threshold we first have to decide if the
    %%% intermediate class 2 encodes background or object pixels. This is
    %%% done by choosing the combination of class probabilities 'pClass'
    %%% that best matches the user input 'pObject'.
    level = linspace(ClassMean(1),ClassMean(3),10000);
    Class1Gaussian = pClass(1) * 1/sqrt(2*pi*ClassStd(1)^2) * exp(-(level - ClassMean(1)).^2/(2*ClassStd(1)^2));
    Class2Gaussian = pClass(2) * 1/sqrt(2*pi*ClassStd(2)^2) * exp(-(level - ClassMean(2)).^2/(2*ClassStd(2)^2));
    Class3Gaussian = pClass(3) * 1/sqrt(2*pi*ClassStd(3)^2) * exp(-(level - ClassMean(3)).^2/(2*ClassStd(3)^2));
    if abs(pClass(2) + pClass(3) - pObject) < abs(pClass(3) - pObject)
        %%% Intermediate class 2 encodes object pixels
        BackgroundDistribution = Class1Gaussian;
        ObjectDistribution = Class2Gaussian + Class3Gaussian;
    else
        %%% Intermediate class 2 encodes background pixels
        BackgroundDistribution = Class1Gaussian + Class2Gaussian;
        ObjectDistribution = Class3Gaussian;
    end
    
    %%% Now, find the threshold at the intersection of the background
    %%% distribution and the object distribution.
    [ignore,index] = min(abs(BackgroundDistribution - ObjectDistribution)); %#ok Ignore MLint
    level = level(index);
end

end


function level = Background(im,pObject)
%%% The threshold is calculated by calculating the mode and multiplying by
%%% 2 (an arbitrary empirical factor). The user will presumably adjust the
%%% multiplication factor as needed.

%%% The following is needed for the adaptive cases where there the image
%%% has been cropped. This must be done within this subfunction, rather
%%% than in the main code prior to sending to this function via blkproc,
%%% because the blkproc function takes a single image as input, so we have
%%% to store the image and its cropmask in a single image variable.
if ndims(im) == 3
    Image = im(:,:,1);
    CropMask = im(:,:,2);
    clear im
    im = Image(CropMask==1);
else im = im(:);
end

if max(im) == min(im)
    level = im(1);
elseif isempty(im)
    %%% im will be empty if the entire image is cropped away by the
    %%% CropMask. I am not sure whether it is better to then set the level
    %%% to 0 or 1. Setting the level to empty causes problems downstream.
    %%% Presumably setting the level to 1 will not cause major problems
    %%% because the other blocks will average it out as we get closer to
    %%% real objects?
    level = 1;
else
    level = 2*mode(im(:));
end

end


function level = RobustBackground(im,pObject)
%%% The threshold is calculated by trimming the top and bottom 25% of
%%% pixels off the image, then calculating the mean and standard deviation
%%% of the remaining image. The threshold is then set at 2 (empirical
%%% value) standard deviations above the mean.

%%% The following is needed for the adaptive cases where there the image
%%% has been cropped. This must be done within this subfunction, rather
%%% than in the main code prior to sending to this function via blkproc,
%%% because the blkproc function takes a single image as input, so we have
%%% to store the image and its cropmask in a single image variable.
if ndims(im) == 3
    Image = im(:,:,1);
    CropMask = im(:,:,2);
    clear im
    im = Image(CropMask==1);
else im = im(:);
end

if max(im) == min(im)
    level = im(1);
elseif isempty(im)
    %%% im will be empty if the entire image is cropped away by the
    %%% CropMask. I am not sure whether it is better to then set the level
    %%% to 0 or 1. Setting the level to empty causes problems downstream.
    %%% Presumably setting the level to 1 will not cause major problems
    %%% because the other blocks will average it out as we get closer to
    %%% real objects?
    level = 1;
else
    %%% First, the image's pixels are sorted from low to high.
    im = sort(im);
    %%% The index of the 5th percentile is calculated, with a minimum of 1.
    LowIndex = max(1,round(.05*length(im)));
    %%% The index of the 95th percentile is calculated, with a maximum of the
    %%% number of pixels in the whole image.
    HighIndex = min(length(im),round(.95*length(im)));
    TrimmedImage = im(LowIndex: HighIndex);
    Mean = mean(TrimmedImage);
    StDev = std(TrimmedImage);
    level = Mean + 2*StDev;
end

end


function level = RidlerCalvard(im,pObject)

%%% The following is needed for the adaptive cases where there the image
%%% has been cropped. This must be done within this subfunction, rather
%%% than in the main code prior to sending to this function via blkproc,
%%% because the blkproc function takes a single image as input, so we have
%%% to store the image and its cropmask in a single image variable.
if ndims(im) == 3
    Image = im(:,:,1);
    CropMask = im(:,:,2);
    clear im
    im = Image(CropMask==1);
else im = im(:);
end

if max(im) == min(im)
    level = im(1);
elseif isempty(im)
    %%% im will be empty if the entire image is cropped away by the
    %%% CropMask. I am not sure whether it is better to then set the level
    %%% to 0 or 1. Setting the level to empty causes problems downstream.
    %%% Presumably setting the level to 1 will not cause major problems
    %%% because the other blocks will average it out as we get closer to
    %%% real objects?
    level = 1;
else
    %%% We want to limit the dynamic range of the image to 256. Otherwise,
    %%% an image with almost all values near zero can give a bad result.
    MinVal = max(im)/256;
    im(im<MinVal) = MinVal;
    im = log(im);
    MinVal = min(im);
    MaxVal = max(im);
    im = (im - MinVal)/(MaxVal - MinVal);
    PreThresh = 0;
    %%% This method needs an initial value to start iterating. Using
    %%% graythresh (Otsu's method) is probably not the best, because the
    %%% Ridler Calvard threshold ends up being too close to this one and in
    %%% most cases has the same exact value.
    NewThresh = graythresh(im);
    delta = 0.00001;
    while abs(PreThresh - NewThresh)>delta
        PreThresh = NewThresh;
        Mean1 = mean(im(im<PreThresh));
        Mean2 = mean(im(im>=PreThresh));
        NewThresh = mean([Mean1,Mean2]);
    end
    level = exp(MinVal + (MaxVal-MinVal)*NewThresh);
end

end
