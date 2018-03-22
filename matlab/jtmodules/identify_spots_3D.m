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
% Help for the CP3D_IdentifySpots module:
% Category: Other
%

% SHORT DESCRIPTION:
% Will Determine Spots in 3D Image stacks after Laplacian Of Gaussian (LoG)
% enhancing of spots. Many of the input arguments are optional. Note that
% while an external script has to be run in order to choose robust values,
% manual selection of the parameters can often yield good estimates, if
% the signal is clear enough.
%
% WHAT DID YOU CALL THE IMAGES YOU WANT TO PROCESS?
% Object detection should be done on this image.
%
% HOW DO YOU WANT TO CALL THE OBJECTS IDENTIFIED BY THIS MODULE?
% This is the name of the the spots identified after thresholding the LoG
% image.
%
% WHICH SPOT ENHANCEMENT DO YOU WANT TO USE?
% You can either enhance spots only within their plane or alternatively
% with the including information from adjacent planes, as described by Raj
% et al. 2009.
%
% OBJECTSIZE
% This value corresponds to the approximate size of you spots in the 2D plane. It should
% be their diameter in pixels. The LoG will use a mask of this size to
% enhance radial signal of that size. Note that in practice the specific value
% does not affect the number of spots, if spots are bright (eg. pixel size 5
% or 6).
%
% INTENSITY QUANTA PER IMAGE
% Prior to spot detection the images are rescaled according to their
% intensity. Since the specific value of minimal and maximal intensities
% are frequently not robust across multiple images, intensity quantile are
% used instead. [0 1] would correspond to using the single dimmest pixel
% for minimal intensity and the single brightest pixel for maximal
% intensity. [0.01 0.90] would mean that the minimum intensity is derived
% from the pixel, which is the 1% brightest pixel of all and that the
% maximum intensity is derived from the pixel, which is the 90% brightest
% pixel .
%
% INTENSITY BORERS FOR INTENSITY RESCALING OF IMAGES
% Most extreme values that the image intensity minimum and image intensity
% maximum (as defined by the quanta) are allowed to have
% [LowestPossibleGreyscaleValueForImageMinimum
% HighestPossibleGreyscaleValueForImageMinimum
% LowestPossibleGreyscaleValueForImageMaximum
% HighestPossibleGreyscaleValueForImageMaximum]
% To ignore individual values, place a NaN.
% Note that these parameters very strongly depend upon the variability of
% your illumination source. When using a robust confocal microscope you can
% set the lowest and highest possible values to values,  which are very
% close (or even identical). If your light source is variable during the
% acquisition (which can be the case with Halogen lamps) you might choose
% less strict borders to detect spots of varying intensites.
%
% THRESHOLD OF SPOT DETECTION
% This is the threshold value for spot detection. The higher it is the more
% stringent your spot detection is. Use external script to determine a
% threshold where the spot number is robust against small variations in the
% threshold.
%
% WHAT IS THE MINIMAL INTENSITY OF A VOXEL WITHIN A SPOT?
% Minimal greyscale value of a voxel, which a voxel has to have in order to
% be recognized to be within a spot. Opitonal argument to make spot
% detection even more robust against very dim spots. In practice, we have
% never observed that this parameter would have any influence on the spot
% detection. However, you might include it as an additional safety measure.
%
%
% [TS]
% *************************************************************************
%
% $Revision: 1879 $
%
% Authors:
%   Nico Battich
%   Thomas Stoeger
%   Lucas Pelkmans
%
% Website: http://www.imls.uzh.ch/research/pelkmans.html
%


classdef identify_spots_3D
    properties (Constant = true)

        VERSION = '0.0.1'

    end

    methods (Static)

        function [occupancy_image, figure] = main(image, log_filter_type, ...
            spot_size, n_planes, ...
            rescale_quantiles, rescale_thresholds, ...
            detection_threshold, ...
            plot)

            % Reset omitted thresholds in +/-Inf
            if rescale_thresholds(1) == 0; rescale_thresholds(1) = -Inf; end;
            if rescale_thresholds(2) == 0; rescale_thresholds(2) = Inf; end;
            if rescale_thresholds(3) == 0; rescale_thresholds(3) = -Inf; end;
            if rescale_thresholds(4) == 0; rescale_thresholds(4) = Inf; end;

            % Set options for function calls
            Options.ObSize = double(spot_size);
            % corresponds to the initial sigma used for spot detection by
            % Sumengen in the initial IdentifyPrimLoG2 module
            Options.Sigma = double((spot_size-1)/3);
            Options.StackDepth = double(n_planes);
            Options.limQuant = double(rescale_quantiles);
            Options.RescaleThr = double(rescale_thresholds);
            Options.ObjIntensityThr = [];
            Options.closeHoles = false;
            Options.ObjSizeThr = [];
            Options.ObjThr = detection_threshold;
            Options.numRatio = 0.20;
            Options.doLog = 0;
            Options.DetectBias = [];

            % Get the LoG filter kernel
            if log_filter_type == '2D'
                op = '2D LoG';
                log_filter = cpsub.fspecialCP3D(op,Options.ObSize,Options.Sigma);
            elseif log_filter_type == '3D'
                op = '3D LoG, Raj';
                log_filter = cpsub.fspecialCP3D(op,Options.ObSize,Options.Sigma,Options.StackDepth);
            else
                error(['Image processing was canceled in identify_spots_3D because filter type was not recognised.']);
            end

            % Segment spots
            [ObjCount SegmentationCC] = cpsub.ObjByFilter( ...
                double(image), log_filter, ...
                Options.ObjThr, Options.limQuant, Options.RescaleThr, ...
                Options.ObjIntensityThr, false, [], Options.DetectBias);

            if SegmentationCC.NumObjects ~= 0 % determine centroid, if at least one object
                tmp = regionprops(SegmentationCC,'Centroid');
                Centroid = cat(1,tmp.Centroid);
                if isempty(Centroid)   % keep the resettign to 0 0 found in other modules to remain consistent
                    Centroid = [0 0];
                end
            end

            occupancy_image = uint16(cpsub.coordinates_to_occupancy_image(Centroid, size(image(:,:,1))));

            if plot
                % make a projection of the image into 2D to plot
                max_proj = max(image,[],3)
                plots = { ...
                jtlib.plotting.create_intensity_image_plot(max_proj, 'ul', 'clip', false), ...
                jtlib.plotting.create_intensity_image_plot(occupancy_image, 'ur'), ...
                jtlib.plotting.create_overlay_image_plot(max_proj, occupancy_image, 'll','clip', false)};
                figure = jtlib.plotting.create_figure(plots);
            else
                figure = '';
            end

        end

    end
end

