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
    % input_image: integer array
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

    % those functions could become privat
    import jtlib.analysePerimeter;
    import jtlib.separateClumps;
    import jtlib.selectClumps;
    import jtlib.removeSmallObjects;
    import jtlib.plotting.save_plotly_figure;
    import jtlib.plotting.constants;

    test_mode = selection_test_mode || perimeter_test_mode;
    if perimeter_test_mode && selection_test_mode
        error('Only one test mode can be active at a time.');
    elseif (test_mode) && ~varargin{4}
        error('Plotting needs to be activated for test mode to work');
    end

    if ~isa(input_mask, 'logical')
        error('Argument "input_mask" must have type logical.')
    end
    % Fill holes
    input_mask = imfill(input_mask, 'holes');

    if ~isa(input_image, 'integer')
        error('Argument "input_image" must have type integer.')
    end
    % Convert to double precision
    rescaled_input_image = double(input_image);

    % Translate angle value
    min_angle = degtorad(min_angle);

    if ~isempty(input_mask)
        
        %--------------
        % Select clumps
        %--------------
        
        masks = zeros([size(input_mask), cutting_passes]);
        cut_mask = zeros([size(input_mask), cutting_passes]);
        selected_clumps = zeros([size(input_mask), cutting_passes]);
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

            % Store selected clumps for plotting
            tmp = zeros(size(input_mask));
            tmp(clumps) = 1;
            tmp(logical(non_clumps(:,:,i))) = 2;
            selected_clumps(:,:,i) = tmp;

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
            cut_mask(:,:,i) = jtlib.separateClumps(clumps, rescaled_input_image, ...
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
        selected_clumps = zeros([size(input_mask), cutting_passes]);
        cut_mask = zeros([size(input_mask), cutting_passes]);
        perimeters = cell(cutting_passes, 1);
        
    end

    if varargin{4}  % plot

    %     if perimeter_test_mode

    %         fig = figure;

    %         if ~isempty(perimeters)
    %             h = cutting_passes;
    %             curv_image = zeros(size(input_mask));
    %             concave_image = zeros(size(input_mask));
    %             angle_image = zeros(size(input_mask));
    %             radius_image = zeros(size(input_mask));
    %             for i = 1:length(perimeters{h})
    %                 matCurrentObjectProps = perimeters{h}{i};%get current object
    %                 imConcaveRegions = bwlabel(matCurrentObjectProps(:,11)==-1);
    %                 imConvexRegions = bwlabel(matCurrentObjectProps(:,11)==1);
    %                 AllRegions = imConcaveRegions+(max(imConcaveRegions)+imConvexRegions).*(imConvexRegions>0);%bwlabel only works binary, therefore label convex, concave seperately, then merger labels
    %                 NumRegions = length(setdiff(unique(AllRegions),0));
    %                 for j = 1:size(matCurrentObjectProps,1)%loop over all pixels of object to plot general properties
    %                     curv_image(matCurrentObjectProps(j,1),matCurrentObjectProps(j,2)) = matCurrentObjectProps(j,9);
    %                     concave_image(matCurrentObjectProps(j,1),matCurrentObjectProps(j,2)) = matCurrentObjectProps(j,11);
    %                 end
    %                 for k = 1:NumRegions%loop over all regions to plot region specific properties
    %                     matCurrentRegionProps = matCurrentObjectProps(AllRegions==k,:);%get current region
    %                     NormCurvature = matCurrentRegionProps(:,9);
    %                     CurrentEqAngle = sum(NormCurvature);
    %                     CurrentEqRadius = length(NormCurvature)/sum(NormCurvature);
    %                     for L = 1:size(matCurrentRegionProps,1)%loop over all pixels in region
    %                         radius_image(matCurrentRegionProps(L,1),matCurrentRegionProps(L,2)) = CurrentEqRadius;
    %                         angle_image(matCurrentRegionProps(L,1),matCurrentRegionProps(L,2)) = radtodeg(CurrentEqAngle);
    %                     end
    %                 end
    %             end
                
    %             subplot(2,2,1);
    %             imagesc(curv_image);
    %             title('Curvature');
    %             caxis([min(curv_image(curv_image>0)), max(curv_image(:))]);
    %             colorbar;
                
    %             subplot(2,2,2);
    %             RGBConvexConcaveImage = cat(3,(concave_image==1),(concave_image==-1),zeros(size(concave_image)));
    %             imagesc(RGBConvexConcaveImage);
    %             title('Convex concave');
    %             % caxis([min(RGBConvexConcaveImage(RGBConvexConcaveImage>0)), max(RGBConvexConcaveImage(:))]);
    %             colorbar;
                
    %             subplot(2,2,3);
    %             imagesc(angle_image);
    %             title('Equivalent angle (degree)');
    %             caxis([min(angle_image(angle_image>0)), max(angle_image(:))]);
    %             colorbar;
                
    %             subplot(2,2,4);
    %             imagesc(radius_image);
    %             title('Equivalent radius');
    %             caxis([min(radius_image(radius_image>0)), max(radius_image(:))]);
    %             colorbar;
    %         end

    %     elseif selection_test_mode

    %         import jtlib.calculateObjectSelectionFeatures;

    %         h = cutting_passes;
    %         mask = masks(:,:,h);
    %         [area, solidity, form_factor] = calculateObjectSelectionFeatures(mask);
    %         solidity_image = rplabel(logical(mask), [], solidity);
    %         form_factor_image = rplabel(logical(mask), [], form_factor);
    %         area_image = rplabel(logical(mask), [], area);

    %         fig = figure;
            
    %         subplot(2,2,1), imagesc(solidity_image);
    %         title('Solidity');
    %         caxis([min(solidity_image(solidity_image>0)), max(solidity_image(:))]);
    %         colorbar;

    %         subplot(2,2,2), imagesc(form_factor_image);
    %         title('Form factor');
    %         caxis([min(form_factor_image(form_factor_image>0)), max(form_factor_image(:))]);
    %         colorbar;

    %         subplot(2,2,3), imagesc(area_image);
    %         title('Area');
    %         caxis([min(area_image(area_image>0)), max(area_image(:))]);
    %         colorbar;

    %         subplot(2,2,4), imagesc(selected_clumps(:,:,h)); colormap('jet');
    %         title('Selected objects');

    %     else
            
    %         B = bwboundaries(output_mask, 'holes');
    %         labeled_mask = label2rgb(bwlabel(output_mask), 'jet', 'k', 'shuffle');

    %         fig = figure;

    %         subplot(2,2,2), imagesc(logical(selected_clumps(:,:,1)==1)),
    %         title('Cut lines on selected clumps in input mask');
    %         hold on
    %         redOutline = cat(3, ones(size(selected_clumps(:,:,1))), ...
    %                             zeros(size(selected_clumps(:,:,1))), ...
    %                             zeros(size(selected_clumps(:,:,1))));
    %         h = imagesc(redOutline);
    %         set(h, 'AlphaData', imdilate(logical(sum(cut_mask, 3)), ...
    %                                      strel('disk', 12)))
    %         hold off
    %         freezeColors

    %         subplot(2,2,1), imagesc(selected_clumps(:,:,1)), colormap('jet'),
    %         title('Selected clumps in input mask');
    %         freezeColors

    %         subplot(2,2,3), imagesc(input_image, ...
    %                                 [quantile(input_image(:), 0.001), ...
    %                                  quantile(input_image(:), 0.999)]),
    %         colormap(gray)
    %         title('Outlines of separated mask');
    %         hold on
    %         for k = 1:length(B)
    %             boundary = B{k};
    %             plot(boundary(:,2), boundary(:,1), 'r', 'LineWidth', 1)
    %         end
    %         hold off
    %         freezeColors

    %         subplot(2,2,4), imagesc(labeled_mask),
    %         title('Labeled separated mask');
    %         freezeColors

    %     end

    % jtlib.plotting.save_figure(fig, varargin{2})
    rf = 1 / 4;

    ds_img = imresize(input_image, rf);
    ds_mask = imresize(uint8(output_mask), rf);  % doesn't work with logical
    [x_dim, y_dim] = size(input_image);
    [ds_x_dim, ds_y_dim] = size(ds_img);

    colors = {{{0, 'rgb(0,0,0)'}, {1, jtlib.plotting.constants.OBJECT_COLOR}}};

    data = {
        struct( ...
            'z', ds_img, ...
            'hoverinfo', 'z', ...
            'zmax', prctile(ds_img, 99.99), ...
            'zmin', 0, ...
            'zauto', false, ...
            'x', linspace(0, x_dim, ds_x_dim), ...
            'y', linspace(0, y_dim, ds_y_dim), ...
            'type', 'heatmap', ...
            'colorscale', 'Greys', ...
            'colorbar', struct( ...
                'yanchor', 'bottom', ...
                'y', 0.57, ...
                'x', 0.43, ...
                'len', 0.43 ...
            ) ...
        ),
        struct( ...
            'z', ds_mask, ...
            'hoverinfo', 'z', ...
            'x', linspace(0, x_dim, ds_x_dim), ...
            'y', linspace(0, y_dim, ds_y_dim), ...
            'type', 'heatmap', ...
            'colorscale', colors, ...
            'showscale', false, ...
            'xaxis', 'x2', ...
            'yaxis', 'y2' ...
        ),
    };
    % TODO: How to visualize cut lines? Scatter? Encode in mask?
    % ds_cut = imresize(cut_mask, rf);
    % [row, col] = find(ds_cut)
    % plot3 = struct(...
    %     'x', col, ...
    %     'y', fliplr(row), ...
    %     'hoverinfo', '', ...
    %     'type', 'scatter', ...
    %     'mode', 'line', ...
    %     'line', struct('color', 'red'), ...
    %     'xaxis', 'x2', ...
    %     'yaxis', 'y2' ...
    % );

    layout = struct(...
        'title', 'Separated objects', ...
        'xaxis1', struct(...
            'domain', [0, 0.43], ...
            'anchor', 'y1' ...
        ), ...
        'yaxis1', struct(...
            'autorange', 'reversed', ...
            'domain', [0.57, 1], ...
            'anchor', 'x1' ...
        ), ...
        'xaxis2', struct(...
            'ticks', '', ...
            'domain', [0.57, 1], ...
            'anchor', 'y2' ...
        ), ...
        'yaxis2', struct(...
            'autorange', 'reversed', ...
            'showticklabels', false, ...
            'domain', [0.57, 1], ...
            'anchor', 'x2' ...
        ) ...
    );

    fig = plotlyfig;
    fig.data = data;
    fig.layout = layout;

    % TODO: figures for test modes

    jtlib.plotting.save_plotly_figure(fig, varargin{2});

    if test_mode
        if selection_test_mode
            msg = 'selection';
        end
        if perimeter_test_mode
            msg = 'perimeter';
        end
        error('Pipeline stopped because module "%s" ran in %s test mode.', m.filename, msg)
    end

end
