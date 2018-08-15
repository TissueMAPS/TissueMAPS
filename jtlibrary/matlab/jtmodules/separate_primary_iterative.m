% Copyright 2018 Scott Berry, University of Zurich
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
%
% ORIGINAL HELP FROM CellProfiler Module
% ***********************************************
% Help for IdentifyPrimIterative
% Category: Object Processing
%
%
% DESCRIPTION:
% Primary identification of objects (nuclei) based on intensity thresholding
% and subsequent separation of clumped objects along watershed lines between
% concave regions.
%
% DETAILS:
% Pixels belonging to nuclei objects can be easily separated form background
% pixels by thresholding an image of a nuclei-specific stain such as DAPI.
% However, this often results in clumps of several individual objects,
% because a single, image-wide threshold value is generally not
% sufficient to nicely separate objects, which lie very close to each other.
% Such clumped objects have a distinct morphology. Compared to individual objects,
% which are more or less round and lie within a certain size range,
% clumped objects are relatively large and display multiple concave regions.
% The intersection of individual objects is most likely a line connecting two
% concave regions. This separating cut line can be found using the watershed
% algorithm. By restricting watershed lines to the area between two concave regions,
% very stable segmentation results can be achieved.
% The module processes the input image as follows:
% 1) Initial objects are identified by simple thresholding.
% 2) Clumped objects are selected on the basis of size and shape features:
%    area, solidity, and form factor.
% 3) The perimeter of selected objects is analyzed and concave
%    regions along the boundary of objects are identified.
% 4) Watershed lines connecting two concave regions are determined.
% 5) All possible cuts along the selected watershed lines are considered and features
%    of each cut line (intensity along the line, angle between concave regions)
%    as well as features of the resulting objects (area/shape) are measured.
% 6) An "optimal" cut line is finally chosen by minimizing a cost function that
%    evaluates the measured features such that the resulting objects have a minimal
%    size and are as round as possible, while the separating line is as straight
%    and short as possible and the intensity along the line as low as possible.
% Note that once an object has been selected for cutting and concave regions
% have been identified, a cut is inevitably made!
% You can control the selection of clumped objects and the identification of
% concave regions by setting the corresponding parameters (see below).
% Test modes are available for both steps that allow choosing parameter values
% in a visually assisted way.
%
%
% PARAMETERS:
% Object name:
% The name you would like to give the objects identified by this module.
%
% Image name:
% The name of the input image in which primary objects should be identified.
%
% Threshold correction factor:
% When the threshold is calculated automatically, it may consistently be
% too stringent or too lenient. You may need to enter an adjustment factor,
% which you empirically determine suitable for your images. The number 1
% means no adjustment, 0 to 1 makes the threshold more lenient, and greater
% than 1 (e.g. 1.3) makes the threshold more stringent. The thresholding method
% used by this module (Otsu algorithm) inherently assumes that 50% of the image
% is covered by objects. If a larger percentage of the image is covered, the
% method will give a slightly biased threshold that may have to be
% corrected using a threshold correction factor.
%
% Lower and upper bounds on threshold:
% Can be used as a safety precaution when the threshold is calculated
% automatically. For example, if there are no objects in the field of view,
% the automatic threshold will be unreasonably low. In such cases, the
% lower bound you enter here will override the automatic threshold.
%
% Cutting passes:
% Each pass, only one cut per concave region is allowed, possibly making it
% necessary to perform additional cutting passes to separate clumps of
% more than two objects.
%
% Debug mode:
% Separation of clumped objects is done on small sub-images.
% By activating the debug mode, you can visually follow steps 2-5 of the algorithm
% outlined above and check whether your parameter settings have the desired effect,
% i.e. whether the correct regions and lines are selected for each object.
%
% Object selection:
% Limits for solidity, form factor, and upper and lower size of objects to be
% selected for cutting. Determine optimal values via test mode.
%
% Test mode for object selection:
% Displays solidity, area, and (transformed) form factor values for each primary
% object identified by thresholding. Pick values from images to fine tune settings.
%
% Perimeter analysis:
% Parameters for detection of concave regions. Determine optimal value via test mode.
% Window size:
% Sliding window for calculating the curvature of objects. Large values result
% in more continuous, smoother but maybe less precise regions, while small values
% give more precise, but smaller and less continuous regions.
% Max equivalent radius:
% Maximum equivalent radius of a concave region to be eligible for cutting.
% Higher values increase sensitivity and result in more cut options.
% Min equivalent segment:
% Minimum equivalent circular fragment (degree) of a concave region to be
% eligible for cutting. Lower values increase sensitivity and result in more cut options.
%
% Test mode for perimeter analysis:
% Displays curvature, convex/concave, equivalent radius and segment of each object.
% Pick values from images to fine tune settings.
%
% DEPENDENCIES:
% PerimeterAnalysis.m
% PerimeterWatershedSegmentation.m
% rplabel.m
% IdentifySecPropagateSubfunction.cpp (must be compiled with mex)
%
%
% AUTHORS:
%  Markus Herrmann
%  Nicolas Battich
%  Thomas Stoeger
%  Anatol Schwab
%
% (c) Pelkmans Lab 2015
%
% $Revision: 1879 $


classdef separate_primary_iterative
    properties (Constant = true)

        VERSION = '0.0.1'

    end

    methods (Static)

        function [separated_objects, figure] = main(primary_objects, ...
            intensity_image, ...
            cutting_passes, max_solidity, min_form_factor, ...
            min_area, max_area, min_area_cut, ...
            sliding_window, filter_size, max_concave_radius, ...
            min_concave_circular_segment, ...
            plot, plot_test_mode, plot_perimeter_analysis)

            path

            %%%%%%%%%%%%%%%%%%%%
            %% CONVERT INPUTS %%
            %%%%%%%%%%%%%%%%%%%%

            if isa(intensity_image, 'uint16')
                OrigImage = double(intensity_image) ./ (2^16 - 1);
            elseif isa(intensity_image, 'uint8')
                OrigImage = double(intensity_image) ./ (2^8 - 1);
            else
                error('Argument "intensity_image" must have type uint8 or uint16.')
            end

            ThreshImage = primary_objects;
            CuttingPasses = cutting_passes;
            SolidityThres = double(max_solidity);
            FormFactorThres = double(min_form_factor);
            UpperSizeThres = double(max_area);
            LowerSizeThres = double(min_area);
            LowerSizeCutThres = double(min_area_cut);
            WindowSize = double(sliding_window);
            smoothingDiskSize = double(filter_size);
            PerimSegEqRadius = double(max_concave_radius);
            PerimSegEqSegment = double(degtorad(min_concave_circular_segment));


            %%%%%%%%%%%%%%%%%%%%
            %% IMAGE ANALYSIS %%
            %%%%%%%%%%%%%%%%%%%%

            %%% Fill holes in objects
            imInputObjects = imfill(double(ThreshImage),'holes');

            if ~isempty(imInputObjects)

                %-------------------------------------------
                % Select objects in input image for cutting
                %-------------------------------------------

                imObjects = zeros([size(imInputObjects),CuttingPasses]);
                imSelected = zeros([size(imInputObjects),CuttingPasses]);
                imCutMask = zeros([size(imInputObjects),CuttingPasses]);
                imCut = zeros([size(imInputObjects),CuttingPasses]);
                imNotCut = zeros([size(imInputObjects),CuttingPasses]);
                objFormFactor = cell(CuttingPasses,1);
                objSolidity = cell(CuttingPasses,1);
                objArea = cell(CuttingPasses,1);
                cellPerimeterProps = cell(CuttingPasses,1);

                for i = 1:CuttingPasses

                    if i==1
                        imObjects(:,:,i) = imInputObjects;
                    else
                        imObjects(:,:,i) = imCut(:,:,i-1);
                    end

                    % Measure basic area/shape features
                    props = regionprops(logical(imObjects(:,:,i)),'Area','Solidity','Perimeter');

                    % Features used for object selection
                    objSolidity{i} = cat(1,props.Solidity);
                    objArea{i} = cat(1,props.Area);
                    tmp = log((4*pi*cat(1,props.Area)) ./ ((cat(1,props.Perimeter)+1).^2))*(-1);%make values positive for easier interpretation of parameter values
                    tmp(tmp<0) = 0;
                    objFormFactor{i} = tmp;

                    % Select objects based on these features (user defined thresholds)
                    obj2cut = objSolidity{i} < SolidityThres & objFormFactor{i} > FormFactorThres ...
                        & objArea{i} > LowerSizeThres & objArea{i} < UpperSizeThres;
                    objNot2cut = ~obj2cut;

                    objSelected = zeros(size(obj2cut));
                    objSelected(obj2cut) = 1;
                    objSelected(objNot2cut) = 2;
                    imSelected(:,:,i) = cpsub.rplabel(logical(imObjects(:,:,i)),[],objSelected);

                    % Create mask image with objects selected for cutting
                    imObj2Cut = zeros(size(OrigImage));
                    imObj2Cut(imSelected(:,:,i)==1) = 1;

                    % Store remaining objects that are omitted from cutting
                    tmp = zeros(size(OrigImage));
                    tmp(imSelected(:,:,i)==2) = 1;
                    imNotCut(:,:,i) = logical(tmp);


                    %-------------
                    % Cut objects
                    %-------------

                    % Smooth image
                    SmoothDisk = getnhood(strel('disk',smoothingDiskSize,0));%minimum that has to be done to avoid problems with bwtraceboundary
                    imObj2Cut = bwlabel(imdilate(imerode(imObj2Cut,SmoothDisk),SmoothDisk));

                    % In rare cases the above smoothing approach creates new, small
                    % objects that cause problems. Let's remove them.
                    props = regionprops(logical(imObj2Cut),'Area');
                    objArea2 = cat(1,props.Area);
                    obj2remove = find(objArea2 < LowerSizeThres);
                    for j = 1:length(obj2remove)
                        imObj2Cut(imObj2Cut==obj2remove(j)) = 0;
                    end
                    imObj2Cut = bwlabel(imObj2Cut);

                    % Separate clumped objects along watershed lines

                    % Note: PerimeterAnalysis cannot handle holes in objects (we may
                    % want to implement this in case of big clumps of many objects).
                    % Sliding window size is linked to object size. Small object sizes
                    % (e.g. in case of images acquired with low magnification) limits
                    % maximal size of the sliding window and thus sensitivity of the
                    % perimeter analysis.

                    % Perform perimeter analysis
                    cellPerimeterProps{i} = cpsub.PerimeterAnalysis(imObj2Cut,WindowSize);

                    % This parameter limits the number of allowed concave regions.
                    % It can serve as a safety measure to prevent runtime problems for
                    % very complex objects.
                    % This could become an input argument in the future!?
                    numRegionTheshold = 30;

                    % Perform the actual segmentation
                    imCutMask(:,:,i) = cpsub.PerimeterWatershedSegmentation(imObj2Cut,OrigImage,cellPerimeterProps{i},PerimSegEqRadius,PerimSegEqSegment,LowerSizeCutThres,numRegionTheshold);
                    imCut(:,:,i) = bwlabel(imObj2Cut.*~imCutMask(:,:,i));

                end

                %-----------------------------------------------
                % Combine objects from different cutting passes
                %-----------------------------------------------

                imCut = logical(imCut(:,:,CuttingPasses));

                if ~isempty(imCut)
                    imErodeMask = bwmorph(imCut,'shrink',inf);
                    imDilatedMask = imErodeMask;
                    imDilatedMask = cpsub.IdentifySecPropagateSubfunction(double(imErodeMask),OrigImage,imCut,1);
                end

                imNotCut = logical(sum(imNotCut,3));% Retrieve objects that were not cut
                imFinalObjects = bwlabel(logical(imDilatedMask + imNotCut));

            else

                cellPerimeterProps = {};
                imFinalObjects = zeros(size(imInputObjects));
                imObjects = zeros([size(imInputObjects),CuttingPasses]);
                imSelected = zeros([size(imInputObjects),CuttingPasses]);
                imCutMask = zeros([size(imInputObjects),CuttingPasses]);
                imCut = zeros([size(imInputObjects),CuttingPasses]);
                imNotCut = zeros([size(imInputObjects),CuttingPasses]);
                objFormFactor = cell(CuttingPasses,1);
                objSolidity = cell(CuttingPasses,1);
                objArea = cell(CuttingPasses,1);
                cellPerimeterProps = cell(CuttingPasses,1);

            end

            %%%%%%%%%%%%%%%%%%%%
            %% CONVERT OUTPUTS %%
            %%%%%%%%%%%%%%%%%%%%

            separated_objects = int32(imFinalObjects);

            if plot
                if plot_perimeter_analysis
                    if ~isempty(cellPerimeterProps)
                        h = 1;
                        imCurvature = zeros(size(OrigImage),'double');
                        imConvexConcave = zeros(size(OrigImage),'double');
                        imAngle = zeros(size(OrigImage),'double');
                        imRadius = zeros(size(OrigImage),'double');
                        for i = 1:length(cellPerimeterProps{h})
                            matCurrentObjectProps = cellPerimeterProps{h}{i};%get current object
                            imConcaveRegions = bwlabel(matCurrentObjectProps(:,11)==-1);
                            imConvexRegions = bwlabel(matCurrentObjectProps(:,11)==1);
                            AllRegions = imConcaveRegions+(max(imConcaveRegions)+imConvexRegions).*(imConvexRegions>0);%bwlabel only works binary, therefore label convex, concave seperately, then merger labels
                            NumRegions = length(setdiff(unique(AllRegions),0));
                            for j = 1:size(matCurrentObjectProps,1)%loop over all pixels of object to plot general properties
                                imCurvature(matCurrentObjectProps(j,1),matCurrentObjectProps(j,2)) = matCurrentObjectProps(j,9);
                                imConvexConcave(matCurrentObjectProps(j,1),matCurrentObjectProps(j,2)) = matCurrentObjectProps(j,11);
                            end
                            for k = 1:NumRegions%loop over all regions to plot region specific properties
                                matCurrentRegionProps = matCurrentObjectProps(AllRegions==k,:);%get current region
                                NormCurvature = matCurrentRegionProps(:,9);
                                CurrentEqAngle = sum(NormCurvature);
                                CurrentEqRadius = length(NormCurvature)/sum(NormCurvature);
                                for L = 1:size(matCurrentRegionProps,1)%loop over all pixels in region
                                    imRadius(matCurrentRegionProps(L,1),matCurrentRegionProps(L,2)) = CurrentEqRadius;
                                    imAngle(matCurrentRegionProps(L,1),matCurrentRegionProps(L,2)) = radtodeg(CurrentEqAngle);
                                end
                            end
                        end

                        plots = {
                            jtlib.plotting.create_intensity_image_plot(imRadius, 'ul'), ...
                            jtlib.plotting.create_intensity_image_plot(imConvexConcave, 'ur'), ...
                            jtlib.plotting.create_intensity_image_plot(imAngle, 'll') ...
                            %jtlib.plotting.create_intensity_image_plot(imCurvature, 'lr') ...
                        };
                        figure = jtlib.plotting.create_figure(plots,'title','radius, concave/convex, angle');
                    end

                elseif plot_test_mode
                    imSolidity = cpsub.rplabel(logical(imObjects(:,:,1)), [], objSolidity{1});
                    imFormFactor = cpsub.rplabel(logical(imObjects(:,:,1)), [], objFormFactor{1});
                    imArea = cpsub.rplabel(logical(imObjects(:,:,1)), [], objArea{1   });
                    plots = {
                        jtlib.plotting.create_intensity_image_plot(imSolidity, 'ul'), ...
                        jtlib.plotting.create_intensity_image_plot(imFormFactor, 'ur'), ...
                        jtlib.plotting.create_intensity_image_plot(imArea, 'll') ...
                    };
                    figure = jtlib.plotting.create_figure(plots,'title','solidity, form factor, area');
                else
                    plots = {
                        jtlib.plotting.create_overlay_image_plot(intensity_image, logical(sum(imCutMask, 3)), 'ur', 'clip', false), ...
                        jtlib.plotting.create_mask_image_plot(imSelected(:,:,1), 'ul'), ...
                        jtlib.plotting.create_mask_image_plot(separated_objects, 'll') ...
                    };
                    figure = jtlib.plotting.create_figure(plots,'title','selected objects to separate, cut lines, output');
                end
            else
                figure = '';
            end

        end

    end
end
