function output_mask = separate_objects(input_mask, input_image, cutting_passes, min_cut_area, ...
                                        max_solidity, min_formfactor, min_area, max_area, selection_test_mode, ...
                                        filter_size, sliding_window_size, min_angle, max_radius, perimeter_test_mode, ...,
                                        varargin)
% Jterator module for separating clumped objects, i.e. continuous pixel regions
% in a binary image that satisfy certain morphological criteria (size and shape).
% 
% Selected clumps are separated along watershed lines in a corresponding
% grayscale image connecting two concave regions. Note that only one fragment
% will be cut of a clump in one cutting pass. 
% 
% This module is based on the "IdentifyPrimaryIterative" CellProfiler module
% as described in Stoeger et al. 2015 [1]_.
% 
% Parameters
% ----------
% input_mask: logical array
%   binary image in which clumps should be separated
% input_image: double array
%   grayscale image that should be used find optimal cut lines
% cutting_passes: double
%   number of cutting rounds that should be applied
% min_cut_area: double
%   minimal area of a cut fragment that should be tolerated, cuts that would
%   result in a smaller fragment will not be performed 
% max_solidity: double
%   maximal solidity value for a continuous pixel region to be considered a clump
% min_formfactor: double
%   minimal form factor value for a continuous pixel region to be considered a clump
%   (it's actually the inverse of the form factor, determine empirically)
% min_area: double
%   minimal area value for a continuous pixel region to be considered a clump
% max_area: double
%   minimal area value for a continuous pixel region to be considered a clump
% selection_test_mode: logical
%   whether selected clumps should be plotted in order to empirically determine 
%   optimal values for `max_solidity`, `min_formfactor`, `min_area` and
%   and `max_area`; no cutting will be performed
% filter_size: double
%   size of the smoothing filter that is applied to the mask prior to
%   perimeter analysis
% sliding_window_size: double
%   size of the sliding window used for perimeter analysis
% min_angle: double
%   minimal angle
% max_radius: double
%   maximal radius of the circle fitting into the concave region
% perimeter_test_mode: logical
%   whether result of the perimeter analysis should be plotted in order to
%   empirically determine optimal values for `min_angle` and `max_radius`;
%   no cutting will be performed
% varargin: cell array
%   additional arguments provided by Jterator:
%   {1}: "data_file", {2}: "figure_file", {3}: "project_dir", {4}: "plot"
% 
% Returns
% -------
% logical array
%   output_mask: binary image with clumps in `input_mask` separated
% 
% References
% ----------
% _[1] Stoeger T, Battich N, Herrmann MD, Yakimovich Y, Pelkmans L.
%      Computer vision for image-based transcriptomics. Methods. 2015

    import jtlib.analysePerimeter;
    import jtlib.separateClumps;
    import jtlib.selectClumps;
    import jtlib.rplabel;
    import jtlib.removeSmallObjects;
    import jtlib.freezeColors;
    import plotting.*;

    if perimeter_test_mode && selection_test_mode
        error('Only one test mode can be active at a time.');
    elseif (perimeter_test_mode || selection_test_mode) && ~varargin{4}
        error('Plotting needs to be activated for test mode to work');
    end

    % Fill holes
    input_mask = imfill(input_mask, 'holes');

    % Translate angle value
    min_angle = degtorad(min_angle);

    if ~isempty(input_mask)
        
        %--------------
        % Select clumps
        %--------------
        
        masks = zeros([size(input_mask), cutting_passes]);
        cut_mask = zeros([size(input_mask), cutting_passes]);
        separated_clumps = zeros([size(input_mask), cutting_passes]);
        non_clumps = zeros([size(input_mask), cutting_passes]);
        perimeters = cell(cutting_passes, 1);

        % Build smoothing disk for filter
        if filter_size < 1
            filter_size = 1;
        end
        smoothing_disk = getnhood(strel('disk', double(filter_size), 0));
        
        for i = 1:cutting_passes

            if i==1
                masks(:,:,i) = input_mask;
            else
                masks(:,:,i) = separated_clumps(:,:,i-1);
            end
            
            % Classify pixel regions into "clumps" and "non_clumps"
            % based on provided morphological criteria.
            % Only "clumps" will be further processed.
            [clumps, non_clumps(:,:,i)] = jtlib.selectClumps(masks(:,:,i), ...
                                                             max_solidity, min_formfactor, ...
                                                             max_area, min_area);

            if i==1
                % Store selected clumps for plotting
                selected_clumps = zeros(size(input_mask));
                selected_clumps(clumps) = 1;
                selected_clumps(logical(non_clumps(:,:,i))) = 2;
            end

            %----------------
            % Separate clumps
            %----------------
            
            % Some smoothing has to be done to avoid problems with perimeter analysis
            clumps = bwlabel(imdilate(imerode(clumps, smoothing_disk), smoothing_disk));
            
            % In rare cases the above smoothing approach creates new, small
            % masks that cause problems. So we remove them.
            clumps = bwlabel(jtlib.removeSmallObjects(clumps, min_area));
            
            % Perform perimeter analysis
            % NOTE: PerimeterAnalysis cannot handle holes in masks (we may
            % want to implement this in case of big clumps of many masks).
            % Sliding window size is linked to object size. Small object sizes
            % (e.g. in case of images acquired with low magnification) limits
            % maximal size of the sliding window and thus sensitivity of the
            % perimeter analysis.
            perimeters{i} = jtlib.analysePerimeter(clumps, sliding_window_size);
            
            % This parameter limits the number of allowed concave regions.
            % It can serve as a safety measure to prevent runtime problems for
            % very complex input images. It could become an input argument.
            max_num_regions = 30;
            
            % Perform the actual segmentation
            cut_mask(:,:,i) = jtlib.separateClumps(clumps, input_image, ...
                                                   perimeters{i}, max_radius, min_angle, ...
                                                   min_cut_area, max_num_regions, 'debugOFF');
            
            separated_clumps(:,:,i) = clumps .* ~cut_mask(:,:,i);

        end
        
        %-----------------------------------------------
        % Combine masks from different cutting passes
        %-----------------------------------------------
            
        % Retrieve masks that were not cut (or already cut)
        all_not_cut = logical(sum(non_clumps, 3));
        output_mask = logical(separated_clumps(:,:,end) + all_not_cut);

        % Smooth once more to get nice object outlines
        output_mask = imdilate(imerode(output_mask, smoothing_disk), smoothing_disk);
        
    else
        
        perimeters = {};
        output_mask = zeros(size(input_mask));
        masks = zeros([size(input_mask), cutting_passes]);
        SelectedObjects = zeros([size(input_mask), cutting_passes]);
        cut_mask = zeros([size(input_mask), cutting_passes]);
        perimeters = cell(cutting_passes, 1);
        
    end

    output_mask = jtlib.removeSmallObjects(output_mask, min_cut_area);


    if varargin{4}  % plot

        if perimeter_test_mode

            % TODO

        elseif selection_test_mode

            % TODO

        else
            
            B = bwboundaries(output_mask, 'holes');
            labeled_mask = label2rgb(bwlabel(output_mask), 'jet', 'k', 'shuffle');

            fig = figure;

            subplot(2,2,2), imagesc(logical(selected_clumps==1)),
            title('Cut lines on selected clumps in input mask');
            hold on
            redOutline = cat(3, ones(size(selected_clumps)), ...
                                zeros(size(selected_clumps)), ...
                                zeros(size(selected_clumps)));
            h = imagesc(redOutline);
            set(h, 'AlphaData', imdilate(logical(sum(cut_mask, 3)), ...
                                         strel('disk', 12)))
            hold off
            freezeColors

            subplot(2,2,1), imagesc(selected_clumps), colormap('jet'),
            title('Selected clumps in input mask');
            freezeColors

            subplot(2,2,3), imagesc(input_image, ...
                                    [quantile(input_image(:), 0.001), ...
                                     quantile(input_image(:), 0.999)]),
            colormap(gray)
            title('Outlines of separated mask');
            hold on
            for k = 1:length(B)
                boundary = B{k};
                plot(boundary(:,2), boundary(:,1), 'r', 'LineWidth', 1)
            end
            hold off
            freezeColors

            subplot(2,2,4), imagesc(labeled_mask),
            title('Labeled separated mask');
            freezeColors

            plotting.save_mpl_figure(fig, varargin{2})

        end

end
