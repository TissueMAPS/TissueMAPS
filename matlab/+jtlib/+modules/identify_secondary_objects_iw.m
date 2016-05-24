function [output_label_image, fig] = identify_secondary_objects_iw(input_label_image, intensity_image, ...
                                                            correction_factors, min_threshold, ...
                                                            plot)

    % Jterator module for identifying secondary objects based on an iterative
    % watershed approach using the primary objects in `input_label_image` as
    % seeds for the watershed algorithm.
    % 
    % This module is based on the "IdentifySecondaryIterative" CellProfiler
    % module as described in Stoeger et al. 2015 [1]_.
    % 
    % Parameters
    % ----------
    % input_label_image: integer
    %   binary image with primary objects that will be used as seeds
    % intensity_image: integer
    %   grayscale image in which objects should be identified
    % correction_factors: double
    %   values by which calculated threshold levels will be multiplied
    % min_threshold: integer
    %     minimal threshold level
    % plot: bool, optional
    %   whether a figure should be generated (default: ``false``)
    % 
    % Returns
    % -------
    % integer
    %   output label image: binary image with identified objects
    % 
    % References
    % ----------
    % _[1] Stoeger T, Battich N, Herrmann MD, Yakimovich Y, Pelkmans L.
    %      Computer vision for image-based transcriptomics. Methods. 2015

    import jtlib.segmentSecondary;
    import jtlib.plotting;

    if nargin < 5
        plot = false;
    end
    fig = '';

    if ~isa(intensity_image, 'integer')
        error('Argument "intensity_image" must have type integer.')
    end
    if isa(intensity_image, 'uint16')
        rescaled_input_image = double(intensity_image) ./ 2^16;
        min_threshold = double(min_threshold) / 2^16;
    elseif isa(intensity_image, 'uint8')
        rescaled_input_image = double(intensity_image) ./ 2^8;
        min_threshold = double(min_threshold) / 2^8;
    else
        error('Argument "intensity_image" must have type uint8 or uint16.')
    end

    if isa(input_label_image, 'logical')
        error('Argument "input_label_image" must be a labeled image.')
    end
    if ~isa(input_label_image, 'integer')
        error('Argument "input_label_image" must have type integer.')
    end
    % NOTE: Use the "label_mask" module to create the labeled image.
    if ~isa(input_label_image, 'int32')
        error('Argument "input_label_image" must have type int32.')
    end
    % Smoothing the label image a bit seems to be necessary 
    input_label_image = double(input_label_image);

    max_threshold = 1;

    % Matlab labels images differently, which causes problems in some cases.
    % Therefore, we relabel primary objects for the identification of
    % secondary objects and create a mapping from new to original labels.
    relabeled_image = bwlabel(input_label_image > 0);
    obj_ids = unique(input_label_image(input_label_image > 0));
    mapping = zeros(length(obj_ids), 1);
    for i = 1:length(obj_ids)
        obj = obj_ids(i);
        new_label = relabeled_image(input_label_image == obj);
        mapping(new_label) = obj;
    end

    output_label_image = segmentSecondary(rescaled_input_image, relabeled_image, relabeled_image, ...
                                          correction_factors, min_threshold, max_threshold);

    % Make sure labels are correct
    unique_input_labels = unique(input_label_image);
    unique_output_labels = unique(output_label_image);
    if setdiff(unique_input_labels, unique_output_labels)
        error('Incorrect number of labels.')
    end

    % Map object labels back.
    final_output_label_image = zeros(size(output_label_image));
    for i = 1:length(mapping)
        obj = mapping(i);
        final_output_label_image(output_label_image == obj) = mapping(obj);
    end

    if plot

        rf = 1 / 4;

        ds_img = imresize(intensity_image, rf);
        ds_labled = imresize(int32(output_label_image), rf);
        [x_dim, y_dim] = size(intensity_image);
        [ds_x_dim, ds_y_dim] = size(ds_img);

        overlay_plot = jtlib.plotting.create_overlay_image_plot( ...
            intensity_image, output_label_image, 'ul' ...
        );
        mask_plot = jtlib.plotting.create_mask_image_plot( ...
            output_label_image > 0, 'ur' ...
        );
        plots = {overlay_plot, mask_plot};

        fig = jtlib.plotting.create_figure(plots);
    end

    output_label_image = int32(output_label_image);

end
