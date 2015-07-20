function [Objects, ObjectIds] = separate_clumps(InputImage,
                                                MaxSolidity, MinFormFactor, MinArea, MaxArea, MinCutArea, ...
                                                FilterSize, SlidingWindow, CircularSegment, MaxRadius)
% Jterator module for segmentating primary objects in an image.
% This module is based on the "IdentifyPrimaryIterative" CellProfiler module
% as described in Stoeger et al. 2015 [1]_.
% 
% Parameters
% ----------
% 
% 
% 
% 
% 
% 
% 
% 
% 
% References
% ----------
% _[1] Stoeger T, Battich N, Herrmann MD, Yakimovich Y, Pelkmans L.
%      Computer vision for image-based transcriptomics. Methods. 2015
% 
    import jtapi.*;
    import jtlib.*;

    % Stick to CellProfiler rescaling
    InputImage = InputImage ./ 2^16;
    MinThreshold = MinThreshold / 2^16;
    MaxThreshold = MaxThreshold / 2^16;

    CircularSegment = degtorad(CircularSegment);

    %% Segment objects
    [IdentifiedNuclei, CutLines, SelectedObjects] = jtlib.segmentprimary(...
                 InputImage, ...
                 CuttingPasses, ...
                 FilterSize, SlidingWindow, CircularSegment, MaxRadius, ...
                 MaxSolidity, MinFormFactor, MinArea, MaxArea, MinCutArea, ...
                 ThresholdCorrection, MinThreshold, MaxThreshold, 'Off');

    IdentifiedNuclei = jtlib.removeSmallObjects(IdentifiedNuclei, MinCutArea);


    if varargin{4}

        B = bwboundaries(IdentifiedNuclei, 'holes');
        imCutShapeObjectsLabel = label2rgb(bwlabel(IdentifiedNuclei), ...
                                           'jet', 'k', 'shuffle');
        AllSelected = SelectedObjects(:,:,1);

        fig = figure;

        subplot(2,2,2), imagesc(logical(AllSelected==1)),
        title('Cut lines on selected original objects');
        hold on
        redOutline = cat(3, ones(size(AllSelected)), ...
                            zeros(size(AllSelected)), ...
                            zeros(size(AllSelected)));
        h = imagesc(redOutline);
        set(h, 'AlphaData', imdilate(logical(sum(CutLines, 3)), ...
                                     strel('disk', 12)))
        hold off
        freezeColors

        subplot(2,2,1), imagesc(AllSelected), colormap('jet'),
        title('Selected original objects');
        freezeColors

        subplot(2,2,3), imagesc(InputImage, ...
                                [quantile(InputImage(:),0.001), ...
                                 quantile(InputImage(:),0.999)]),
        colormap(gray)
        title('Outlines of separated objects');
        hold on
        for k = 1:length(B)
            boundary = B{k};
            plot(boundary(:,2), boundary(:,1), 'r', 'LineWidth', 1)
        end
        hold off
        freezeColors

        subplot(2,2,4), imagesc(imCutShapeObjectsLabel),
        title('Separated objects');
        freezeColors

        jtapi.savefigure(varargin{3}, fig)

end
