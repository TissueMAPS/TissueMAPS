% Copyright 2017 Scott Berry, University of Zurich
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
%
% Help for the IdentifySpots2D module:
% Category: Object Processing
%
% SHORT DESCRIPTION:
% Detects spots as destribed by Battich et al., 2013.
% ***********************************************
% Will Determine Spots in 2D Image stacks after Laplacian Of Gaussian (LoG)
% enhancing of spots. Many of the input arguments are optional. Note that
% while an external script has to be run in order to choose robust values,
% manual selection of the parameters can often yield good estimates, if
% the signal is clear enough.
%
% WHAT DID YOU CALL THE IMAGES YOU WANT TO PROCESS?
% Object detection should be done on this image.
%
% HOW DO YOU WANT TO CALL THE OBJECTS IDENTIFIED PRIOR TO DEBLENDING?
% This is the name of the the spots identified after thresholding the LoG
% image.
%
% HOW DO YOU WANT TO CALL THE OBJECTS IDENTIFIED AFTER DEBLENDING?
% Optional. Deblending can be done after spot detection to separate close
% objects. The algorithm is based upon SourceExtractor. To skip this step,
% insert / as name of the object.
%
% OBJECTSIZE
% This value corresponds to the approximate size of you spots. It should
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
% HOW MANY STEPS OF DEBLENDING DO YOU WANT TO DO?
% The amount of deblending steps, which are done. The higher it is the less
% likely it is that two adjacent spots are not separated. The default of 30
% works very well (and we did not see improvement on our images with higher
% values). Note that the number of deblending steps is the main determinant
% of computational time for this module.
%
% EDIT 30/6/17 (Scott Berry)
%
% NOTE: THE FOLLOWING TWO OPTIONS ARE NO LONGER EXPOSED IN THE INTERFACE
% ======================================================================
%
% WHAT IS THE MINIMAL INTENSITY OF A PIXEL WITHIN A SPOT?
% Minimal greyscale value of a pixel, which a pixel has to have in order to
% be recognized to be within a spot. Opitonal argument to make spot
% detection even more robust against very dim spots. In practice, we have
% never observed that this parameter would have any influence on the spot
% detection. However, you might include it as an additional safety measure.
%
% WHICH IMAGE DO YOU WANT TO USE AS A REFERENCE FOR SPOT BIAS CORRECTION?
% Here you can name a correction matrix which counteracts bias of the spot
% correction across the field of view. Note that such a correction matrix
% has to be loaded previously by a separate module, such as
% LOADSINGLEMATRIX
%
%
% Authors:
%   Nico Battich
%   Thomas Stoeger
%   Lucas Pelkmans
%
% Website: http://www.imls.uzh.ch/research/pelkmans.html
%
% The design of this module largely follows a IdentifyPrimLoG2 by
% Baris Sumengen


classdef identify_spots_2D
    properties (Constant = true)

        VERSION = '0.0.2'

    end

    methods (Static)

        function [spots, spots_deblend, figure] = main(image, spot_size, ...
         rescale_quantiles, rescale_thresholds, ...
         detection_threshold, deblending_steps, ...
         plot)

            path

            % Reset omitted thresholds in +/-Inf
            if rescale_thresholds(1) == 0; rescale_thresholds(1) = -Inf; end;
            if rescale_thresholds(2) == 0; rescale_thresholds(2) = Inf; end;
            if rescale_thresholds(3) == 0; rescale_thresholds(3) = -Inf; end;
            if rescale_thresholds(4) == 0; rescale_thresholds(4) = Inf; end;

            % Set options for function calls
            Options.ObSize = double(spot_size);
            Options.limQuant = double(rescale_quantiles);
            Options.RescaleThr = double(rescale_thresholds);
            Options.ObjIntensityThr = [];
            Options.closeHoles = false;
            Options.ObjSizeThr = [];
            Options.ObjThr = detection_threshold;
            Options.StepNumber = deblending_steps;
            Options.numRatio = 0.20;
            Options.doLog = 0;
            Options.DetectBias = [];

            % Get the LoG filter kernel
            log_filter = cpsub.fspecialCP3D('2D LoG',Options.ObSize);

            % Peform initial segmentation of spots
            [ObjCount{1} SegmentationCC{1} FiltImage] = cpsub.ObjByFilter( ...
                double(image), log_filter, ...
                Options.ObjThr, Options.limQuant, Options.RescaleThr, ...
                Options.ObjIntensityThr, true, [], Options.DetectBias)
            spots = int32(labelmatrix(SegmentationCC{1}));

            % Security check, if conversion is correct
            if max(spots(:)) ~= ObjCount{1}
                error(['Image processing was canceled in identify_spots_2D because conversion of segmentation format failed.'])
            end

            % Deblend spots
            if deblending_steps > 0 && ObjCount{1} > 0
                spots_deblend = int32(cpsub.SourceExtractorDeblend( ...
                    double(image), SegmentationCC{1}, FiltImage, Options));
            else
                spots_deblend = zeros(size(image),'int32')
            end

            if plot
                plots = { ...
                jtlib.plotting.create_intensity_image_plot(image, 'ul'), ...
                jtlib.plotting.create_mask_image_plot(spots_deblend, 'ur'), ...
                jtlib.plotting.create_mask_image_plot(spots, 'll')};
                figure = jtlib.plotting.create_figure(plots);
            else
                figure = '';
            end

        end

    end
end
