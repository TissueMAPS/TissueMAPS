function output_label_image = identify_secondary_objects_iw(input_label_image, input_image, ...
                                                            correction_factors, min_threshold, ...
                                                            varargin)

    % Jterator module for identifying secondary objects based on an iterative
    % watershed approach using the primary objects in `input_label_image` as
    % seeds for the watershed algorithm.
    % 
    % This module is based on the "IdentifySecondaryIterative" CellProfiler
    % module as described in Stoeger et al. 2015 [1]_.
    % 
    % Parameters
    % ----------
    % input_label_image: integer array
    %   binary image with primary objects that will be used as seeds
    % input_image: integer array
    %   grayscale image in which objects should be identified
    % correction_factors: double array
    %   values by which calculated threshold levels will be multiplied
    % min_threshold: integer
    %     minimal threshold level
    % varargin: cell array
    %   additional arguments provided by Jterator:
    %   {1}: "data_file", {2}: "figure_file", {3}: "experiment_dir", {4}: "plot", {5} "job_id"
    % 
    % Returns
    % -------
    % integer array
    %   output label image: binary image with identified objects
    % 
    % References
    % ----------
    % _[1] Stoeger T, Battich N, Herrmann MD, Yakimovich Y, Pelkmans L.
    %      Computer vision for image-based transcriptomics. Methods. 2015

    import jtlib.segmentSecondary;
    import jtlib.freezeColors;
    import jtlib.plotting.save_figure;

    if ~isa(input_image, 'integer')
        error('Argument "input_image" must have type integer.')
    end
    if isa(input_image, 'uint16')
        input_image = double(input_image) ./ 2^16;
        min_threshold = double(min_threshold) / 2^16;
    elseif isa(input_image, 'uint8')
        input_image = double(input_image) ./ 2^8;
        min_threshold = double(min_threshold) / 2^8;
    else
        error('Argument "input_image" must have type uint8 or uint16.')
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
    input_label_image = double(input_label_image);

    max_threshold = 1;

    output_label_image = segmentSecondary(input_image, input_label_image, input_label_image, ...
                                          correction_factors, min_threshold, max_threshold); 

    if varargin{4}
        B = bwboundaries(output_label_image, 'holes');
        labeled_cells = label2rgb(bwlabel(output_label_image),'jet','k','shuffle');
        
        fig = figure;

        subplot(2,1,1), imagesc(input_image, [quantile(input_image(:),0.01) quantile(input_image(:),0.99)]);
        colormap(gray);
        title('Outlines of identified objects');
        hold on
        for k = 1:length(B)
            boundary = B{k};
            plot(boundary(:,2), boundary(:,1), 'r', 'LineWidth', 1);
        end
        hold off
        freezeColors

        subplot(2,1,2), imagesc(labeled_cells);
        title('Identified objects');
        freezeColors

        jtlib.plotting.save_figure(fig, varargin{2});
    end

    output_label_image = int32(output_label_image);

end
