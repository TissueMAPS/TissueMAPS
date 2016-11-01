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
function [secondaryLabelMatrixImage, editedPrimaryBinaryImage, thresholdArray] = segmentSecondary(origImage, prelimPrimaryLabelMatrixImage, editedPrimaryLabelMatrixImage, ...
                                                                                                    thresholdCorrection, minimumThreshold, maximumThreshold)

    % SEGMENTSECONDARY identifies objects (e.g. cell edges)
    % using "seed" objects identified by an Identify Primary module (e.g. nuclei).
    %
    % [SECONDARYLABELMATRIXIMAGE, EDITEDPRIMARYBINARYIMAGE, THRESHOLDARRAY] = SEGMENTSECONDARY(ORIGIMAGE, PRELIMPRIMARYLABELMATRIXIMAGE, EDITEDPRIMARYLABELMATRIXIMAGE, ...
    %                                                                               THRESHOLDCORRECTION, MINIMUMTHRESHOLD, MAXIMUMTHRESHOLD)
    %
    % See help of Cell Profiler's IdentifySecondary module for more details.
    %
    % In contrast to the original module, sequential rounds of watershedding are
    % done. The outcome will be a very precise cell outline segmentation, which
    % does not need a lot of human supervision (and thus greatly reduces
    % working time). However, since this module can take up to 30 min on a
    % single image, you might not want to use it, if you do not have access to
    % massive parallel computing facilities.
    %
    %
    % Parameters:
    % -----------
    %
    %   ORIGIMAGE                           Grey-scale image (double)
    %   PRELIMPRIMARYLABELMATRIXIMAGE       Label image with primary objects
    %   EDITEDPRIMARYLABELMATRIXIMAGE       Label image with primary objects
    %   THRESHOLDCORRECTION                 Array of threshold correction values
    %   MININMUMTHRESHOLD                   Lower bound threshold value
    %   MAXIMUMTHRESHOLD                    Upper bound threshold value
    %
    %   Note: when used outside of CellProfiler values of ORIGIMAGE
    %   and MININMUMTHRESHOLD/MAXIMUMTHRESHOLD have to be rescaled between 0-1!
    %
    % Returns:
    % --------
    %
    %   SECONDARYLABELMATRIXIMAGE           Label image 
    %   EDITEDPRIMARYBINARYIMAGE            Label image  
    %   THRESHOLDARRAY                      Array of used threshold values
    %
    % Usage:
    % ------
    %
    % This module identifies secondary objects by sequential watershedding.
    % This allows to combine the advantage of a high threshold correction
    % factor (correct allocation of pixels to cells within crowded regions)
    % with the advantage of a low threshold correction factor (detection of
    % cellular periphery in sparse regions).
    %
    % To prevent false positives, if very few primary objects are present,
    % limits for threshold can be used.
    %
    %
    % SUGGESTION TO FIND MINIMAL BACKGROUND - ROBUST CAMERA / IMAGING
    % CONDITIONS
    % If using sCMOS cameras, the intensity value, which corresponds to
    % background signal from the chip is ~100 greyscale values. Distinctive
    % cell-specific signal from the cell outline stain can usually be detected
    % at ~125 greyscale values. The minimal background value thus corresponds
    % to 0.0019 (125/2^16)
    %
    % SUGGESTION TO FIND MINIMAL BACKGROUND - VIA IDENTIFYSECONDARY
    % Get lowest threshold, which does not yet recognize background as
    % cells.
    % Make a CP pipeline with several IdentifySecondary modules. In each one
    % select a different threshold correction value. Use OTSU GLOBAL and
    % WATERSHEDDING
    % Now start the pipeline. Of all modules, which do not recognize the
    % background, use the one with the smallest threshold correction value
    % (for us this is frequently around 0.5). Then manually write down the
    % exact threshold value of this module. It will be displayed in the
    % window opened by this module.
    %
    % Do not bother, whether the cells are correctly segmented.
    % The only important point is that the outline of the
    % cell has to be detected fully. Make sure that the test image is
    % representative of your assay. Usually spreading cells do require a much
    % lower threshold value than cells in crowded environments.
    %
    % SETTING UP THE IDENTIFYSECONDARYITERATIVE MODULE
    %
    % THRESHOLD CORRECTION FACTORS. IN DESCENDING RANKING.
    % Should indicate many different thresholds.
    % It starts with the most stringent and starts with the lowest.
    % The lowest one should be so low that it would recognize the
    % background as an object.
    %
    % Note that you do not care about:
    % x the number of thresholds. The more, the better. Use supercomputing.
    % Applying around 20 different ones usually gives very robust results. You
    % can not select too many thresholds. You can save days of manual work by
    % not selecting (a single) individual threshold(s).
    % x the specific value of the lowest threshold: The lowest value has to be
    % lower than the lowest threshold correction, which you tested previously.
    % It should be a threshold value that recognizes the background. The
    % separation from the background will be done by a later option. If the
    % last threshold correction value is too high, the periphery of spreading
    % cells might be missed.
    %
    % An example for the range would be 1.1 1.05 1 0.95 0.9 0.85 0.8 0.75 0.7
    % 0.6 0.58 0.55 0.50 0.45 0.4 0.35 0.3 0.25
    %
    % Usually the best gain in segmentation quality per threshold is achieved
    % with threshold correction factors close to the threshold correction
    % factor, which you would choose in the normal IdentifySecondary module
    %
    % LOWER AND UPPER BONDS ON THRESHOLD.
    % These values correspond to the minimal and maximal values that a
    % threshold is allowed to have. They have the format
    % SmallestThreshold,HighestThreshold
    % For SmallestThreshold you should use the value obtained in c). Leaving
    % the maximal value at 1 has worked fine for us all the time. Setting a
    % minimal value will prevent recognition of the background as an object
    %
    %
    % *************************************************************************
    %
    %
    % How it works>
    % This is a heavily adjusted version of the original IdentifySecondary module
    % It also has lower memory requirements and fixes some bugs of the original
    % module (shrinkage of nuclei, expansion of surrounding objects discarded by
    % DiscardSinglePixel)
    %
    % 0) Obtain masks with proper foreground objects.
    %
    % 1)sequential watershedding
    %
    % 2)Then one label image is constructed. If a pixel is part of different
    % objects at given threshold (which is likely in cell rich regions), it will be
    % allocated to the threshold which was defined prior. eg. if thresholds
    % specifications were 1 and 0.5 it would be attributed to the object
    % identified with a threshold of 1. If threshold specification was 0.5 1
    % it would be attributed to the object identified at 0.5
    %
    % 3) Cleaning up step. It could happen that an object would end up
    % separated into multiple fragments (which in most cases would be
    % biologically meaningless). Thus all fragments except the one, which
    % includes the primary object, are set to background
    %
    %
    % Authors:
    % --------
    %   Thomas Stoeger
    %   Nico Battich
    %   Markus Herrmann
    %   Lucas Pelkmans

    dbstop if error

    import jtlib.calculateThresholdLevel;
    import jtlib.removeSmallObjects;

    UseAsLabelInCaseNoBackgroundPresent = prelimPrimaryLabelMatrixImage;
    if any(prelimPrimaryLabelMatrixImage(:) == 0)
        originalSegmentationHasBackground = true;
    else
        originalSegmentationHasBackground = false;
    end

    numThresholdsToTest = length(thresholdCorrection);
    thresholdArray = cell(numThresholdsToTest,1); % [modified by PLab to include multiple thresholds]

    % Former optional inputs, which in practice have lost any relevance
    ThresholdMethod = 'Otsu Global';
    pObject = 10;
    % [PLab] force to use minimal treshold value of 0 and maximum of 1, to ensure
    % equal thresholding for all tested tresholds
    % [MDH] make independent of handles!
    thresholdArray{1} = calculateThresholdLevel(ThresholdMethod, ...
                                       pObject, 0, 1, ...
                                       thresholdCorrection(1), ...
                                       origImage, ...
                                       []);

    %%%% [PLab] start modification for obtaining multiple thresholds  %%%%%%%%%%%%%%%%%
    if numThresholdsToTest>1
        for k=2:numThresholdsToTest
            %%% STEP 1a: Marks at least some of the background
            refThreshold = thresholdArray{1};
            thresholdArray{k} = refThreshold .* thresholdCorrection(k) ./thresholdCorrection(1);
        end
    end


    numericThresholds = cell2mat(thresholdArray);
    f = numericThresholds > maximumThreshold;
    numericThresholds(f) = maximumThreshold;

    f = numericThresholds < minimumThreshold;
    numericThresholds(f) = minimumThreshold;

    numericThresholds = unique(numericThresholds);
    numericThresholds = sort(numericThresholds, 'descend');

    thresholdArray = arrayfun(@(x) {x}, numericThresholds,'UniformOutput',true);
    numThresholdsToTest = length(thresholdArray);

    %%%% [PLab] end modification for obtaining multiple thresholds  %%%%%%%%%%%%%%%%%


    %%%% [PLab] Start modification> DISMISS only border  %%%%%%%%%%%%%%%%%%%%%%
    %%% Preliminary objects, which were not identified as object proper, still
    %%% serve as seeds for allocating pixels to secondary object. While this
    %%% makes sense for nuclei, which were discared in the primary module due to
    %%% their location at the image border (and have a surrounding cytoplasm),
    %%% it can lead to wrong segmenations, if a false positive nucleus, that was
    %%% filtered away , eg. by the DiscardSinglePixel... module , was present

    %%% corrsponds to one line from STEP 10, moved up. Allows proper
    %%% initialzing for reconstitution
    %%% Converts the editedPrimaryBinaryImage to binary.
    editedPrimaryBinaryImage = im2bw(editedPrimaryLabelMatrixImage,.5);

    % Replace the way the mask PrelimPrimaryBinaryImage is generated
    %%% Use a shared line from STEP 0. This will allow proper initializing for reconstitution.
    %%% Converts the prelimPrimaryLabelMatrixImage to binary.
    %%% OLD> PrelimPrimaryBinaryImage = im2bw(prelimPrimaryLabelMatrixImage,.5);

    %%% Get IDs of objects at image border
    R= prelimPrimaryLabelMatrixImage([1 end],:);
    C= prelimPrimaryLabelMatrixImage(:,[1 end]);
    BoderObjIDs = unique([R C']);
    isBackground = BoderObjIDs == 0;

    if any(isBackground)
        BoderObjIDs = BoderObjIDs(~isBackground);
    end
    clear R; clear C;

    PrelimPrimaryBinaryImage = false(size(editedPrimaryBinaryImage));

    f =     ismember(prelimPrimaryLabelMatrixImage,BoderObjIDs) | ... % objects at border
        editedPrimaryBinaryImage;            % proper objects

    PrelimPrimaryBinaryImage(f) = true;


    %%%% [PLab] End modification> DISMISS only border  %%%%%%%%%%%%%%%%%%%%%




    %%%% [PLab] %%%%%%%%%%%%% Start of SHARED code for precalculations %%%%%%%%%%%
    % note that fragments of original function were replaced by PLab to prevent
    % redundant calculations

    % drawnow

    %%% Creates the structuring element that will be used for dilation.
    StructuringElement = strel('square',3);
    %%% Dilates the Primary Binary Image by one pixel (8 neighborhood).
    DilatedPrimaryBinaryImage = imdilate(PrelimPrimaryBinaryImage, StructuringElement);
    %%% Subtracts the PrelimPrimaryBinaryImage from the DilatedPrimaryBinaryImage,
    %%% which leaves the PrimaryObjectOutlines.
    PrimaryObjectOutlines = DilatedPrimaryBinaryImage - PrelimPrimaryBinaryImage;


    %%% STEP 4: Calculate the Sobel image, which reflects gradients, which will
    %%% be used for the watershedding function.
    % drawnow
    %%% Calculates the 2 sobel filters.  The sobel filter is directional, so it
    %%% is used in both the horizontal & vertical directions and then the
    %%% results are combined.
    filter1 = fspecial('sobel');
    filter2 = filter1';
    %%% Applies each of the sobel filters to the original image.
    I1 = imfilter(origImage, filter1);
    I2 = imfilter(origImage, filter2);
    %%% Adds the two images.
    %%% The Sobel operator results in negative values, so the absolute values
    %%% are calculated to prevent errors in future steps.
    AbsSobeledImage = abs(I1) + abs(I2);
    clear I1; clear I2;                  %%% [PLab] hack. save memory

    %%%% [PLab] %%%%%%%%%%%%% End of SHARED code for precalculations %%%%%%%%%%%


    %%%%%% [PLab] %%%%%%%%%%%%%%%  ITERATION CODE %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    % intialize output

    cellFinalLabelMatrixImage = cell(numThresholdsToTest,1);

    if originalSegmentationHasBackground == false
        FinalLabelMatrixImage = UseAsLabelInCaseNoBackgroundPresent;
    else % standard case
        
        for k=1:numThresholdsToTest
            
            % STEP 0
            %%% Thresholds the original image.
            ThresholdedOrigImage = origImage > thresholdArray{k};
            
            
            %%% STEP 1b: Marks at least some of the background
            
            %%% Inverts the image.
            InvertedThresholdedOrigImage = imcomplement(ThresholdedOrigImage);
            clear ThresholdedOrigImage;             %%% [PLab] hack. save memory.
            
            %%% STEP 3: Produce the marker image which will be used for the first
            %%% watershed.
            % drawnow
            %%% Combines the foreground markers and the background markers.
            BinaryMarkerImagePre = PrelimPrimaryBinaryImage | InvertedThresholdedOrigImage;
            %%% Overlays the PrimaryObjectOutlines to maintain distinctions between each
            %%% primary object and the background.
            BinaryMarkerImage = BinaryMarkerImagePre;
            clear BinaryMarkerImagePre;             %%% [PLab] hack. save memory.
            BinaryMarkerImage(PrimaryObjectOutlines == 1) = 0;
            
            
            %%% STEP 5: Perform the first watershed.
            % drawnow
            
            %%% Overlays the foreground and background markers
            Overlaid = imimposemin(AbsSobeledImage, BinaryMarkerImage);
            clear BinaryMarkerImage;  %%% [PLab] hack. save memory.
            
            %%% Perform the watershed on the marked absolute-value Sobel Image.
            BlackWatershedLinesPre = watershed(Overlaid);
            clear Overlaid;                 %%% [PLab] hack. save memory.
            
            %%% Bug workaround (see step 9).
            %%% [PLab, WATERSHED BUG IN VERSION 2011A (Windows only) OR HIGHER HAS BEEN FIXED. SO CHECK VERSION FIRST]
            if verLessThan('matlab', '7.12.0') && ispc()
                BlackWatershedLinesPre2 = im2bw(BlackWatershedLinesPre,.5);
                BlackWatershedLines = bwlabel(BlackWatershedLinesPre2);
                %%% [PLab] hack. save memory.
                clear BlackWatershedLinesPre2 BlackWatershedLinesPre;
            else
                %%% [BS, QUICK AND DIRTY HACK FROM PEKLMANS]
                BlackWatershedLines = double(BlackWatershedLinesPre);
                %%% [PLab] hack. save memory.
                clear BlackWatershedLinesPre;
                %%% END OF BS-HACK BUGFIX FOR VERSION 2011 AND LATER?
            end
            
            %%% STEP 6: Identify and extract the secondary objects, using the watershed
            %%% lines.
            % drawnow
            %%% The BlackWatershedLines image is a label matrix where the watershed
            %%% lines = 0 and each distinct object is assigned a number starting at 1.
            %%% This image is converted to a binary image where all the objects = 1.
            SecondaryObjects1 = im2bw(BlackWatershedLines,.5);
            %%% [PLab] hack. save memory.
            clear BlackWatershedLines;
            %%% Identifies objects in the binary image using bwlabel.
            %%% Note: Matlab suggests that in some circumstances bwlabeln is faster
            %%% than bwlabel, even for 2D images.  I found that in this case it is
            %%% about 10 times slower.
            LabelMatrixImage1 = bwlabel(SecondaryObjects1,4);
            %%% [PLab] hack. save memory.
            clear SecondaryObjects1;
            % drawnow
            
            %%% STEP 7: Discarding background "objects".  The first watershed function
            %%% simply divides up the image into regions.  Most of these regions
            %%% correspond to actual objects, but there are big blocks of background
            %%% that are recognized as objects. These can be distinguished from actual
            %%% objects because they do not overlap a primary object.
            
            %%% The following changes all the labels in LabelMatrixImage1 to match the
            %%% centers they enclose (from PrelimPrimaryBinaryImage), and marks as background
            %%% any labeled regions that don't overlap a center. This function assumes
            %%% that every center is entirely contained in one labeled area.  The
            %%% results if otherwise may not be well-defined. The non-background labels
            %%% will be renumbered according to the center they enclose.
            
            %%% Finds the locations and labels for different regions.
            area_locations = find(LabelMatrixImage1);
            area_labels = LabelMatrixImage1(area_locations);
            %%% Creates a sparse matrix with column as label and row as location,
            %%% with the value of the center at (I,J) if location I has label J.
            %%% Taking the maximum of this matrix gives the largest valued center
            %%% overlapping a particular label.  Tacking on a zero and pushing
            %%% labels through the resulting map removes any background regions.
            map = [0 full(max(sparse(area_locations, area_labels, PrelimPrimaryBinaryImage(area_locations))))];
            
            ActualObjectsBinaryImage = map(LabelMatrixImage1 + 1);
            clear area_labels area_locations map;              %%% [PLab] hack. save memory.
            
            
            %%% STEP 8: Produce the marker image which will be used for the second
            %%% watershed.
            % drawnow
            %%% The module has now produced a binary image of actual secondary
            %%% objects.  The gradient (Sobel) image was used for watershedding, which
            %%% produces very nice divisions between objects that are clumped, but it
            %%% is too stringent at the edges of objects that are isolated, and at the
            %%% edges of clumps of objects. Therefore, the stringently identified
            %%% secondary objects are used as markers for a second round of
            %%% watershedding, this time based on the original (intensity) image rather
            %%% than the gradient image.
            
            %%% Creates the structuring element that will be used for dilation.
            StructuringElement = strel('square',3);
            %%% Dilates the Primary Binary Image by one pixel (8 neighborhood).
            DilatedActualObjectsBinaryImage = imdilate(ActualObjectsBinaryImage, StructuringElement);
            %%% Subtracts the PrelimPrimaryBinaryImage from the DilatedPrimaryBinaryImage,
            %%% which leaves the PrimaryObjectOutlines.
            ActualObjectOutlines = DilatedActualObjectsBinaryImage - ActualObjectsBinaryImage;
            %%% [PLab] hack. save memory.
            clear DilatedActualObjectsBinaryImage;
            %%% Produces the marker image which will be used for the watershed. The
            %%% foreground markers are taken from the ActualObjectsBinaryImage; the
            %%% background markers are taken from the same image as used in the first
            %%% round of watershedding: InvertedThresholdedOrigImage.
            BinaryMarkerImagePre2 = ActualObjectsBinaryImage | InvertedThresholdedOrigImage;
            %%% [PLab] hack. save memory.
            clear InvertedThresholdedOrigImage ActualObjectsBinaryImage;
            %%% Overlays the ActualObjectOutlines to maintain distinctions between each
            %%% secondary object and the background.
            BinaryMarkerImage2 = BinaryMarkerImagePre2;
            %%% [PLab] hack. save memory.
            clear BinaryMarkerImagePre2;
            
            BinaryMarkerImage2(ActualObjectOutlines == 1) = 0;
            
            %%% STEP 9: Perform the second watershed.
            %%% As described above, the second watershed is performed on the original
            %%% intensity image rather than on a gradient (Sobel) image.
            % drawnow
            %%% Inverts the original image.
            InvertedOrigImage = imcomplement(origImage);
            %%% Overlays the foreground and background markers onto the
            %%% InvertedOrigImage, so there are black secondary object markers on top
            %%% of each dark secondary object, with black background.
            MarkedInvertedOrigImage = imimposemin(InvertedOrigImage, BinaryMarkerImage2);
            %%% [PLab] hack. save memory.
            clear BinaryMarkerImage2 BinaryMarkerImage2;
            
            %%% Performs the watershed on the MarkedInvertedOrigImage.
            SecondWatershedPre = watershed(MarkedInvertedOrigImage);
            %%% [PLab] hack.save memory
            clear MarkedInvertedOrigImage;
            %%% BUG WORKAROUND:
            %%% There is a bug in the watershed function of Matlab that often results in
            %%% the label matrix result having two objects labeled with the same label.
            %%% I am not sure whether it is a bug in how the watershed image is
            %%% produced (it seems so: the resulting objects often are nowhere near the
            %%% regional minima) or whether it is simply a problem in the final label
            %%% matrix calculation. Matlab has been informed of this issue and has
            %%% confirmed that it is a bug (February 2004). I think that it is a
            %%% reasonable fix to convert the result of the watershed to binary and
            %%% remake the label matrix so that each label is used only once. In later
            %%% steps, inappropriate regions are weeded out anyway.
            
            %%% [PLab, WATERSHED BUG IN VERSION 2011A (Windows only) OR HIGHER HAS BEEN FIXED. SO CHECK VERSION FIRST]
            if verLessThan('matlab', '7.12.0') && ispc()
                SecondWatershedPre2 = im2bw(SecondWatershedPre,.5);
                SecondWatershed = bwlabel(SecondWatershedPre2);
                %%% [PLab] hack.save memory
                clear SecondWatershedPre2;
            else
                %%% [BS, QUICK AND DIRTY HACK FROM PEKLMANS]
                SecondWatershed = double(SecondWatershedPre);
                %%% END OF BS-HACK BUGFIX FOR VERSION 2011 AND LATER?
            end
            %%% [PLab] hack.save memory
            clear SecondWatershedPre;
            % drawnow
            
            %%% STEP 10: As in step 7, remove objects that are actually background
            %%% objects.  See step 7 for description. This time, the edited primary object image is
            %%% used rather than the preliminary one, so that objects whose nuclei are
            %%% on the edge of the image and who are larger or smaller than the
            %%% specified size are discarded.
            
            %%% Finds the locations and labels for different regions.
            area_locations2 = find(SecondWatershed);
            area_labels2 = SecondWatershed(area_locations2);
            %%% Creates a sparse matrix with column as label and row as location,
            %%% with the value of the center at (I,J) if location I has label J.
            %%% Taking the maximum of this matrix gives the largest valued center
            %%% overlapping a particular label.  Tacking on a zero and pushing
            %%% labels through the resulting map removes any background regions.
            map2 = [0 full(max(sparse(area_locations2, area_labels2, editedPrimaryBinaryImage(area_locations2))))];
            FinalBinaryImagePre = map2(SecondWatershed + 1);
            %%% [PLab] hack. save memory
            clear SecondWatershed area_labels2 map2;
            
            %%% Fills holes in the FinalBinaryPre image.
            FinalBinaryImage = imfill(FinalBinaryImagePre, 'holes');
            %%% [PLab] hack. save memory
            clear FinalBinaryImagePre;
            %%% Converts the image to label matrix format. Even if the above step
            %%% is excluded (filling holes), it is still necessary to do this in order
            %%% to "compact" the label matrix: this way, each number corresponds to an
            %%% object, with no numbers skipped.
            ActualObjectsLabelMatrixImage3 = bwlabel(FinalBinaryImage);
            %%% [PLab] hack. save memory
            clear FinalBinaryImage;
            %%% The final objects are relabeled so that their numbers
            %%% correspond to the numbers used for nuclei.
            %%% For each object, one label and one label location is acquired and
            %%% stored.
            [LabelsUsed,LabelLocations] = unique(editedPrimaryLabelMatrixImage);
            %%% The +1 increment accounts for the fact that there are zeros in the
            %%% image, while the LabelsUsed starts at 1.
            LabelsUsed(ActualObjectsLabelMatrixImage3(LabelLocations(2:end))+1) = editedPrimaryLabelMatrixImage(LabelLocations(2:end));
            FinalLabelMatrixImagePre = LabelsUsed(ActualObjectsLabelMatrixImage3+1);
            %%% [PLab] hack. save memory
            clear FinalBinaryImage LabelsUsed LabelLocations;
            %%% The following is a workaround for what seems to be a bug in the
            %%% watershed function: very very rarely two nuclei end up sharing one
            %%% "cell" object, so that one of the nuclei ends up without a
            %%% corresponding cell.  I am trying to determine why this happens exactly.
            %%% When the cell is measured, the area (and other
            %%% measurements) are recorded as [], which causes problems when dependent
            %%% measurements (e.g. perimeter/area) are attempted.  It results in divide
            %%% by zero errors and the mean area = NaN and so on.  So, the Primary
            %%% label matrix image (where it is nonzero) is written onto the Final cell
            %%% label matrix image pre so that every primary object has at least some
            %%% pixels of secondary object.
            FinalLabelMatrixImage = FinalLabelMatrixImagePre;
            %%% [PLab] hack. save memory
            clear FinalLabelMatrixImagePre;
            FinalLabelMatrixImage(editedPrimaryLabelMatrixImage ~= 0) = editedPrimaryLabelMatrixImage(editedPrimaryLabelMatrixImage ~= 0);
            
            %[PLab] insert to allow easy collecition of segmentations at all
            %different thresholds
            if max(FinalLabelMatrixImage(:))<intmax('uint16')
                cellFinalLabelMatrixImage{k} = uint16(FinalLabelMatrixImage); % if used for cells, few objects, reduce memory load
            else
                cellFinalLabelMatrixImage{k} = FinalLabelMatrixImage;
            end
            
            clear FinalLabelMatrixImage; % memory==low
            
        end
        %%%% [PLab] %%%%%%%%%%%%%%%%%%%%%%%%%%%%% End of iteration  %%%%%%%%%%%
        
        clear AbsSobeledImage;
        clear PrelimPrimaryBinaryImage;
        
        
        
        %%%% [PLab] %%%%%%%%%% COMBINE SEGEMENTATIONS  Start  %%%%%%%%%%%
        
        % this code combines knowledge of about the segementation at individual
        % thresholds to one common segmentation, which will be superior and
        % combines the advantage of high threshold (less/no false allocation to
        % wrong cell) with the advantage of low thresholds (inclusion of cell
        % boundaries)
        
        
        % A) Reverse projection
        FinalLabelMatrixImage  = zeros(size(cellFinalLabelMatrixImage{1}),'double');
        for k=numThresholdsToTest:-1:1
            f = cellFinalLabelMatrixImage{k} ~=0;
            FinalLabelMatrixImage(f) = cellFinalLabelMatrixImage{k}(f);
        end
        
        % B) Make sure objects are separted
        
        % Dilate segmentation by one pixel and reassign IDs. This is necessary
        % because edge detection is done in next step to create 0 intensity pixels
        % between IDa-IDb. However, without dilation to background, background-IDa
        % boundaries would become extended in next step
        
        % use code from spot qualtiy control showSpotsInControl.m
        DistanceToDilate = 1;
        %%% Creates the structuring element using the user-specified size.
        StructuringElementMini = strel('disk', DistanceToDilate);
        %%% Dilates the preliminary label matrix image (edited for small only).
        DilatedPrelimSecObjectLabelMatrixImageMini = imdilate(FinalLabelMatrixImage, StructuringElementMini);
        %%% Converts to binary.
        DilatedPrelimSecObjectBinaryImageMini = im2bw(DilatedPrelimSecObjectLabelMatrixImageMini,.5);
        %%% Computes nearest neighbor image of nuclei centers so that the dividing
        %%% line between secondary objects is halfway between them rather than
        %%% favoring the primary object with the greater label number.
        [~, Labels] = bwdist(full(FinalLabelMatrixImage>0)); % We want to ignore MLint error checking for this line.
        %%% Remaps labels in Labels to labels in FinalLabelMatrixImage.
        if max(Labels(:)) == 0,
            Labels = ones(size(Labels));
        end
        ExpandedRelabeledDilatedPrelimSecObjectImageMini = FinalLabelMatrixImage(Labels);
        RelabeledDilatedPrelimSecObjectImageMini = zeros(size(ExpandedRelabeledDilatedPrelimSecObjectImageMini));
        RelabeledDilatedPrelimSecObjectImageMini(DilatedPrelimSecObjectBinaryImageMini) = ExpandedRelabeledDilatedPrelimSecObjectImageMini(DilatedPrelimSecObjectBinaryImageMini);
        % Stop using code from showSpotsInControl.m
        clear ExpandedRelabeledDilatedPrelimSecObjectImageMini;
        % Create Boundaries
        
        I1 = imfilter(RelabeledDilatedPrelimSecObjectImageMini, filter1);   % [PLab] reuse sobel filters from above
        I2 = imfilter(RelabeledDilatedPrelimSecObjectImageMini, filter2);
        AbsSobeledImage = abs(I1) + abs(I2);
        clear I1; clear I2;                  %%% [PLab] hack. save memory
        edgeImage = AbsSobeledImage>0;    % detect edges
        FinalLabelMatrixImage = RelabeledDilatedPrelimSecObjectImageMini .* ~edgeImage;   % set edges in Labelmatrix to zero
        clear Labels; clear ExpandedRelabeledDilatedPrelimSecObjectImageMini;
        clear edgeImage;
        
        if max(FinalLabelMatrixImage(:)) ~= 0       % check if an object is present Empty Image Handling
            hasObjects = true;
        else
            hasObjects = false;
        end
        
        if hasObjects == true
            % C) Remove regions no longer connected to the primary object
            % Process individual segmented objects en-block to speed up computation
            distanceToObjectMax = 3;
            loadedImage = FinalLabelMatrixImage;
            props = regionprops(loadedImage,'BoundingBox');
            BoxPerObj = cat(1,props.BoundingBox);
            
            N = floor(BoxPerObj(:,2)-distanceToObjectMax-1);                    f = N < 1;                      N(f) = 1;
            S = ceil(BoxPerObj(:,2)+BoxPerObj(:,4)+distanceToObjectMax+1);      f = S > size(loadedImage,1);    S(f) = size(loadedImage,1);
            W = floor(BoxPerObj(:,1)-distanceToObjectMax-1);                    f = W < 1;                      W(f) = 1;
            E = ceil(BoxPerObj(:,1)+BoxPerObj(:,3)+distanceToObjectMax+1);      f = E > size(loadedImage,2);    E(f) = size(loadedImage,2);
            
            % create empty output
            FinalLabelMatrixImage2  = zeros(size(FinalLabelMatrixImage));
            numObjects =size(BoxPerObj,1);
            if numObjects >= 1  % if objects present
                patchForPrimaryObject = false(1,numObjects);
                for k=1: numObjects  % loop through individual objects to safe computation
                    miniImage = FinalLabelMatrixImage(N(k):S(k),W(k):E(k));
                    bwminiImage = miniImage>0;
                    labelmini = bwlabel(bwminiImage);
                    
                    miniImageNuclei = editedPrimaryLabelMatrixImage(N(k):S(k),W(k):E(k));
                    bwParentOfInterest = miniImageNuclei == k;
                    
                    % now find the most frequent value. note that preobject will not be
                    % completely within child at border of image
                    
                    NewChildID = labelmini(bwParentOfInterest);
                    
                    if isequal(NewChildID,0) % [PLab 150120: only compute if an object is found, see other comments marked by PLab 150120 for explanation]
                        patchForPrimaryObject(k) = true;
                    else
                        NewChildID = NewChildID(NewChildID>0);
                        WithParentIX = mode(NewChildID); % [PLab 150120: note that MODE gives different behavior on 0 input in new MATLAB versions]
                        bwOutCellBody = labelmini == WithParentIX;
                        
                        % now map back the linear indices
                        [r, c] = find(bwOutCellBody);
                        
                        % get indices for final image (note that mini image might have
                        % permitted regions of other cells).
                        r = r-1+N(k);
                        c = c-1+W(k);
                        w = sub2ind(size(FinalLabelMatrixImage2),r,c);
                        
                        % Update Working copy of Final Segmentation image based on linear indices.
                        FinalLabelMatrixImage2(w) = k;
                    end
                end
                
            end
            % Now mimik standard outupt of calculations of standard module
            FinalLabelMatrixImage = FinalLabelMatrixImage2;
            
            
        end
        
        % duplicate penultimate row and column. Thus pixels at border will carry
        % an object ID (and are detected by iBrain function to discard border cells);
        FinalLabelMatrixImage(:,1)= FinalLabelMatrixImage(:,2);
        FinalLabelMatrixImage(:,end)= FinalLabelMatrixImage(:,(end-1));
        FinalLabelMatrixImage(1,:)= FinalLabelMatrixImage(2,:);
        FinalLabelMatrixImage(end,:)= FinalLabelMatrixImage((end-1),:);
        
        
        % [PLab 150120: ensure that every primary object has a secondary object:
        % in case that no secondary object could be found (which is related to
        % CP's behavior of using rim of primary object as seed), use the primary
        % segmentation of the missing objects as the secondary object]
        % Note: this fix is after extending the pixels at the border since
        % sometimes small 1 -pixel objects, which are lost, are sitting at the
        % border of an image (and thus would be overwritten)
        
        if hasObjects == true       % check if an object is present Empty Image Handling
            if numObjects >= 1
                if any(patchForPrimaryObject)
                    % [PLab]: note the conservative behavior to track individual missing
                    % objects; this is intended for backward compatibility, while a simple
                    % query for missing IDs would be faster, it would be more general and
                    % thus potentially conflict with the segementation results of prior
                    % pipelines (in other regions than the objects lost by prior / default
                    % behavior of segmentation modules)
                    IDsOfObjectsToPatch = find(patchForPrimaryObject);
                    needsToIncludePrimary = ismember(editedPrimaryLabelMatrixImage,IDsOfObjectsToPatch);
                    FinalLabelMatrixImage(needsToIncludePrimary) =  editedPrimaryLabelMatrixImage(needsToIncludePrimary);
                end
            end
        end
    end
    %%%% [PLab] %%%%%%%%%% COMBINE SEGEMENTATIONS  End  %%%%%%%%%%%

    secondaryLabelMatrixImage = FinalLabelMatrixImage;

end
