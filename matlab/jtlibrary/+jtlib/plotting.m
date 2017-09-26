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
classdef plotting

    properties (Constant)

        OBJECT_COLOR = 'rgb(255, 191, 0)';

        PLOT_HEIGHT = 0.43;
        PLOT_WIDTH = 0.43;

        FIGURE_WIDTH = 800;
        FIGURE_HEIGHT = 800;

        PLOT_POSITION_MAPPING = struct( ...
            'ul', {{'y1', 'x1'}}, ...
            'ur', {{'y2', 'x2'}}, ...
            'll', {{'y3', 'x3'}}, ...
            'lr', {{'y4', 'x4'}} ...
        );

        COLORBAR_POSITION_MAPPING = struct( ...
            'ul', [1-jtlib.plotting.PLOT_HEIGHT, jtlib.plotting.PLOT_WIDTH], ...
            'ur', [1-jtlib.plotting.PLOT_HEIGHT, 1], ...
            'll', [0, jtlib.plotting.PLOT_WIDTH], ...
            'lr', [0, 1] ...
        );

        IMAGE_RESIZE_FACTOR = 4;

    end


    % methods (Static, Access=private, Hidden)

    methods (Static)

        function plot = create_histogram_plot(data, position, varargin)
            % Create a histogram plot.
            %
            % Parameters
            % ----------
            % data: array
            %     data that should be plotted
            % position: Array[integer]
            %     one-based figure coordinate that defines the relative position of the
            %     plot within the figure; ``'ul'`` -> upper left, ``'ur'`` -> upper
            %     right, ``'ll'`` lower left, ``'lr'`` -> lower right
            % varargin: cell array, optional
            %     optional arguments as key-value pairs; the value after
            %     "color" specifies the color that should be used for
            %     the bins (default: ``'grey'``)
            %
            % Returns
            % -------
            % struct
            color_index = strcmp(varargin, 'color');
            if any(color_index)
                color = varargin{color_index+1};
            else
                color = 'grey';
            end

            pos = jtlib.plotting.PLOT_POSITION_MAPPING.(position);
            plot = struct( ...
                        'type', 'histogram', ...
                        'x', data, ...
                        'marker', struct( ...
                            'color', color ...
                        ), ...
                        'showlegend', false, ...
                        'yaxis', pos{1}, ...
                        'xaxis', pos{2} ...
            );

        end

        function plot = create_scatter_plot(y_data, x_data, position, varargin)
            % Create a scatter plot.
            %
            % Parameters
            % ----------
            % y_data: array
            %     data that should be plotted along the y-axis
            % x_data: array
            %     data that should be plotted along the x-axis
            % position: Array[integer]
            %     one-based figure coordinate that defines the relative position of the
            %     plot within the figure; ``'ul'`` -> upper left, ``'ur'`` -> upper
            %     right, ``'ll'`` lower left, ``'lr'`` -> lower right
            % varargin: cell array, optional
            %     optional arguments as key-value pairs; the value after
            %     "color" specifies the color of markers
            %     (class: char, default: ``'grey'``) and the value after
            %     "marker_size" the size of the marker
            %     (class: integer, default: ``4``)
            %
            % Returns
            % -------
            % struct
            color_index = strcmp(varargin, 'color');
            if any(color_index)
                color = varargin{color_index+1};
            else
                color = 'grey';
            end
            size_index = strcmp(varargin, 'marker_size');
            if any(size_index)
                marker_size = varargin{size_index+1};
            else
                marker_size = 4;
            end

            pos = jtlib.plotting.PLOT_POSITION_MAPPING.(position);
            plot = struct( ...
                        'type', 'scatter', ...
                        'x', x_data, ...
                        'y', y_data, ...
                        'marker', struct( ...
                            'color', color, ...
                            'size', marker_size ...
                        ), ...
                        'showlegend', false, ...
                        'yaxis', pos{1}, ...
                        'xaxis', pos{2} ...
            );

        end

        function plot = create_line_plot(y_data, x_data, position, varargin)
            % Create a line plot.
            %
            % Parameters
            % ----------
            % y_data: array
            %     data that should be plotted along the y-axis
            % x_data: array
            %     data that should be plotted along the x-axis
            % position: Array[integer]
            %     one-based figure coordinate that defines the relative position of the
            %     plot within the figure; ``'ul'`` -> upper left, ``'ur'`` -> upper
            %     right, ``'ll'`` lower left, ``'lr'`` -> lower right
            % varargin: cell array, optional
            %     optional arguments as key-value pairs; the value after
            %     "color" specifies the color of the line
            %     (class: char, default: ``'grey'``) and the value after
            %     "line_width" the size of the points
            %     (class: integer, default: ``4``)
            %
            % Returns
            % -------
            % struct
            color_index = strcmp(varargin, 'color');
            if any(color_index)
                color = varargin{color_index+1};
            else
                color = 'grey';
            end
            width_index = strcmp(varargin, 'line_width');
            if any(width_index)
                line_width = varargin{width_index+1};
            else
                line_width = 4;
            end

            pos = jtlib.plotting.PLOT_POSITION_MAPPING.(position);
            plot = struct( ...
                        'type', 'scatter', ...
                        'x', x_data, ...
                        'y', y_data, ...
                        'marker', struct( ...
                            'size', 0 ...
                        ), ...
                        'line', struct( ...
                            'color', color, ...
                            'width', line_width ...
                        ), ...
                        'showlegend', false, ...
                        'yaxis', pos{1}, ...
                        'xaxis', pos{2} ...
            );
        end

        function plot = create_intensity_image_plot(image, position, varargin)
            % Create a heatmap plot for an intensity image.
            % Intensity values will be encode with greyscale colors.
            %
            % Paramters
            % ---------
            % image: Array[uint8 or uint16]
            %     2D intensity image
            % position: Array[integer]
            %     one-based figure coordinate that defines the relative position of the
            %     plot within the figure; ``'ul'`` -> upper left, ``'ur'`` -> upper
            %     right, ``'ll'`` lower left, ``'lr'`` -> lower right
            % varargin: cell array, optional
            %     optional arguments as key-value pairs; the value after
            %     "clip" specifies whether intensity values should be
            %     clipped (class: logical, default: ``true``) and the value
            %     after "clip_value" the threshold level
            %     (class: integer, defaults to the 99th percentile)
            %
            % Returns
            % -------
            % struct
            clip_index = strcmp(varargin, 'clip');
            if any(clip_index)
                clip = varargin{clip_index+1};
            else
                clip = true;
            end
            clip_val_index = strcmp(varargin, 'clip_value');
            if any(clip_val_index)
                clip_value = varargin{clip_val_index+1};
            else
                if clip
                    clip_value = prctile(image(:), 99);
                else
                    clip_value = max(image(:));
                end
            end

            ds_img = imresize(image, 1/jtlib.plotting.IMAGE_RESIZE_FACTOR);
            dims = size(image);
            ds_dims = size(ds_img);

            pos = jtlib.plotting.PLOT_POSITION_MAPPING.(position);
            col_pos = jtlib.plotting.COLORBAR_POSITION_MAPPING.(position);

            plot = struct( ...
                        'type', 'heatmap', ...
                        'z', ds_img, ...
                        'hoverinfo', 'z', ...
                        'zmax', clip_value, ...
                        'zmin', 0, ...
                        'zauto', false, ...
                        'colorscale', 'Greys', ...
                        'colorbar', struct( ...
                            'yanchor', 'bottom', ...
                            'thickness', 10, ...
                            'y', col_pos(1), ...
                            'x', col_pos(2), ...
                            'len', jtlib.plotting.PLOT_HEIGHT ...
                        ), ...
                        'y', linspace(0, dims(1), ds_dims(1)), ...
                        'x', linspace(0, dims(2), ds_dims(2)), ...
                        'showlegend', false, ...
                        'yaxis', pos{1}, ...
                        'xaxis', pos{2} ...
            );

        end

        function plot = create_mask_image_plot(mask, position, varargin)
            % Create a heatmap plot for a mask image.
            % Unique object labels will be encoded with RGB colors.

            % Paramters
            % ---------
            % mask: Array[integer]
            %     binary or labeled 2D mask image
            % position: Array[integer]
            %     one-based figure coordinate that defines the relative position of the
            %     plot within the figure; ``'ul'`` -> upper left, ``'ur'`` -> upper
            %     right, ``'ll'`` lower left, ``'lr'`` -> lower right
            % varargin: cell array, optional
            %     optional arguments as key-value pairs; the value after
            %     "colorscale" specifies the color map that should be
            %     used to visually highlight objects in the mask image
            %     (class: Cell[Cell[integer, char]], defaults to
            %     a naice qualitative color map)
            %
            % Returns
            % -------
            % struct
            n_objects = length(unique(mask(mask > 0)));
            colorscale_index = strcmp(varargin, 'colorscale');
            if any(colorscale_index)
                colorscale = varargin{colorscale_index+1};
            else
                if n_objects == 1
                    colorscale = {{0, 'rgb(0,0,0)'}, {1, jtlib.plotting.OBJECT_COLOR}};
                else
                    colorscale = jtlib.plotting.create_colorscale('summer', n_objects);
                    colorscale{1} = {0, 'rgb(0,0,0)'};
                end
            end

            ds_mask = imresize(uint8(mask), 1/jtlib.plotting.IMAGE_RESIZE_FACTOR);
            dims = size(mask);
            ds_dims = size(ds_mask);

            pos = jtlib.plotting.PLOT_POSITION_MAPPING.(position);
            col_pos = jtlib.plotting.COLORBAR_POSITION_MAPPING.(position);

            plot = struct( ...
                        'type', 'heatmap', ...
                        'z', ds_mask, ...
                        'hoverinfo', 'z', ...
                        'colorscale', {colorscale}, ...
                        'colorbar', struct( ...
                            'yanchor', 'bottom', ...
                            'thickness', 10, ...
                            'y', col_pos(1), ...
                            'x', col_pos(2), ...
                            'len', jtlib.plotting.PLOT_HEIGHT ...
                        ), ...
                        'y', linspace(0, dims(1), ds_dims(1)), ...
                        'x', linspace(0, dims(2), ds_dims(2)), ...
                        'showlegend', false, ...
                        'yaxis', pos{1}, ...
                        'xaxis', pos{2} ...
            );

        end

        function plot = create_overlay_image_plot(image, mask, position, varargin)
            % Create an intensity image plot and overlay the outlines of a mask
            % in color on top of the greyscale plot.
            %
            % Parameters
            % ----------
            % image: Array[uint8 or uint16]
            %     2D intensity image
            % position: Array[integer]
            %     one-based figure coordinate that defines the relative position of the
            %     plot within the figure; ``'ul'`` -> upper left, ``'ur'`` -> upper
            %     right, ``'ll'`` lower left, ``'lr'`` -> lower right
            % varargin: cell array, optional
            %     optional arguments as key-value pairs; the value after
            %     "clip" specifies whether intensity values should be
            %     clipped (class: logical, default: ``true``), the value
            %     after  "clip_value" the threshold level
            %     (class: integer, defaults to the 99th percentile), and the
            %     value after "color" the color that should be used for the
            %     object outlines that will be superimposed on the image
            %     (class: char, defaults to the value of `OBJECT_COLOR`)
            %
            % Returns
            % -------
            % struct
            clip_index = strcmp(varargin, 'clip');
            if any(clip_index)
                clip = varargin{clip_index+1};
            else
                clip = true;
            end
            clip_val_index = strcmp(varargin, 'clip_value');
            if any(clip_val_index)
                clip_value = varargin{clip_val_index+1};
            else
                if clip
                    clip_value = prctile(image(:), 99);
                else
                    clip_value = max(image(:));
                end
            end
            color_index = strcmp(varargin, 'color');
            if any(color_index)
                color = varargin{color_index+1};
            else
                color = jtlib.plotting.OBJECT_COLOR;
            end

            ds_img = imresize(image, 1/jtlib.plotting.IMAGE_RESIZE_FACTOR);
            ds_mask = imresize(uint8(mask), 1/jtlib.plotting.IMAGE_RESIZE_FACTOR);
            dims = size(mask);
            ds_dims = size(ds_mask);

            pos = jtlib.plotting.PLOT_POSITION_MAPPING.(position);
            col_pos = jtlib.plotting.COLORBAR_POSITION_MAPPING.(position);

            ds_out_img = bwperim(ds_mask);
            ds_img(ds_out_img) = 0;

            colorscale = jtlib.plotting.create_colorscale('gray', clip_value);
            colorscale{1}{2} = color;

            plot = struct( ...
                        'type', 'heatmap', ...
                        'z', ds_img, ...
                        'hoverinfo', 'z', ...
                        'zmax', clip_value, ...
                        'zmin', 0, ...
                        'zauto', false, ...
                        'colorscale', {colorscale}, ...
                        'colorbar', struct( ...
                            'yanchor', 'bottom', ...
                            'thickness', 10, ...
                            'y', col_pos(1), ...
                            'x', col_pos(2), ...
                            'len', jtlib.plotting.PLOT_HEIGHT ...
                        ), ...
                        'y', linspace(0, dims(1), ds_dims(1)), ...
                        'x', linspace(0, dims(2), ds_dims(2)), ...
                        'showlegend', false, ...
                        'yaxis', pos{1}, ...
                        'xaxis', pos{2} ...
            );

        end

        function fig = create_figure(plots, varargin)
            % Create a figure based on one or more subplots.
            % Plots will be arranged as a 2x2 grid.
            %
            % Parameters
            % ----------
            % plots: Cell[struct or Cell[struct]]
            %     subplots that should be used in the figure; subplots can be further
            %     nested, i.e. grouped together in case they should be combined at the
            %     same figure position
            % varargin: cell, optional
            %     optional arguments as key-value pairs; the value after
            %     "plot_positions" specifies the relative position of each plot
            %     in the figure
            %     (class: Cell[char], default: ``{'ul', 'ur', 'll', 'lr'}``),
            %     the value after "plot_is_image" specifies whether the plot
            %     represents an image
            %     (class: Array[bool], default: ``[true, true, true, true]``),
            %     and the value after "title" specifies the title of the figure
            %     (class: char, default: ``''``)
            %
            % Returns
            % -------
            % char
            %     JSON representation of the figure

            plot_pos_index = strcmp(varargin, 'plot_positions');
            if any(plot_pos_index)
                plot_positions = varargin{plot_pos_index+1};
            else
                plot_positions = {'ul', 'ur', 'll', 'lr'};
            end
            plot_isim_index = strcmp(varargin, 'plot_is_image');
            if any(plot_isim_index)
                plot_is_image = varargin{plot_isim_index+1};
            else
                plot_is_image = [true, true, true, true];
            end
            title_index = strcmp(varargin, 'title');
            if any(title_index)
                title = varargin{title_index+1};
            else
                title = '';
            end

            data = {};
            layout = struct('title', title);
            for i = 1:length(plots)
                if plot_positions{i} == 'ul'
                    layout.xaxis1 = struct( ...
                            'domain', [0, jtlib.plotting.PLOT_WIDTH], ...
                            'anchor', 'y1' ...
                    );
                    layout.yaxis1 = struct( ...
                            'domain', [1-jtlib.plotting.PLOT_HEIGHT, 1], ...
                            'anchor', 'x1' ...
                    );
                    if plot_is_image(i)
                        layout.yaxis1.autorange = 'reversed';
                    end
                elseif plot_positions{i} == 'ur'
                    layout.xaxis2 = struct( ...
                            'domain', [1-jtlib.plotting.PLOT_WIDTH, 1], ...
                            'anchor', 'y2' ...
                    );
                    layout.yaxis2 = struct( ...
                            'domain', [1-jtlib.plotting.PLOT_HEIGHT, 1], ...
                            'anchor', 'x2' ...
                    );
                    if plot_is_image(i)
                        layout.yaxis2.autorange = 'reversed';
                    end
                elseif plot_positions{i} == 'll'
                    layout.xaxis3 = struct( ...
                            'domain', [0, jtlib.plotting.PLOT_WIDTH], ...
                            'anchor', 'y3' ...
                    );
                    layout.yaxis3 = struct( ...
                            'domain', [0, jtlib.plotting.PLOT_HEIGHT], ...
                            'anchor', 'x3' ...
                    );
                    if plot_is_image(i)
                        layout.yaxis3.autorange = 'reversed';
                    end
                elseif plot_positions{i} == 'lr'
                    layout.xaxis4 = struct( ...
                            'domain', [1-jtlib.plotting.PLOT_WIDTH, 1], ...
                            'anchor', 'y4' ...
                    );
                    layout.yaxis4 = struct( ...
                            'domain', [0, jtlib.plotting.PLOT_HEIGHT], ...
                            'anchor', 'x4' ...
                    );
                    if plot_is_image(i)
                        layout.yaxis4.autorange = 'reversed';
                    end
                else
                    error('Options for values of argument "plot_positions" are: %s', ...
                          strjoin({'ul', 'ur', 'll', 'lr'}, ', '))
                end

                % Flatten potentially nested list
                data = [data, plots{i}];

            end

            jdata = escapechars(m2json(data));
            jlayout = escapechars(m2json(layout));
            fig = sprintf('{"data": %s, "layout": %s}', jdata, jlayout);

        end

        function colorscale = create_colorscale(name, n)
            % Create a color palette in the format required by
            % `plotly <https://plot.ly/python/>`_ based on a
            % `Matlab colormap <mathworks.com/help/matlab/ref/colormap.html>`_.
            % 
            % Parameters
            % ----------
            % name: str
            %     name of a Matlab colormap, e.g. ``'gray'``
            % n: integer
            %     number of colors (default: ``256``)
            % 
            % Returns
            % -------
            % Cell[Cell[double, char]]
            %     RGB color palette
            % 
            % Examples
            % --------
            % >>>create_colorscale('gray', 5)
            % {{0.0, 'rgb(255,255,255)'},
            %  {0.25, 'rgb(216,216,216)'},
            %  {0.5, 'rgb(149,149,149)'},
            %  {0.75, 'rgb(82,82,82)'},
            %  {1.0, 'rgb(0,0,0)'}}

            if nargin == 1
                n = 256;
            end
            cmap = feval(name, 256);
            indices = round(linspace(1, 256, n));
            vals = linspace(0, 1, n);
            rgb_values = round(cmap(indices, :) * 255);
            colorscale = cellfun(@(v, rgb) {v, sprintf('rgb(%d,%d,%d)', rgb(1), rgb(1), rgb(1))}, ...
                                 num2cell(vals'), mat2cell(rgb_values, ones(1, n), 3), 'UniformOutput', false);
        end

        function imLabel = rplabel(imLogical, imIntensity, Property, logarithm)
            %REGIONPROPS_LABEL_IMAGE creates a label image based on a measurement of
            %the regionprops function.
            %
            %   When PROPERTY is provided as string:
            %   L = REGIONPROPS_LABEL_IMAGE(BW,I,PROPERTY,LOGARITHM) calls the
            %   regionprops function using the input images BW and I and the input
            %   property PROPERTY. It returns a matrix L, of the same size as BW,
            %   containing labels of the measured PROPERTY for the connected objects in
            %   BW. 
            %   
            %   When PROPERTY is provided as matrix:
            %   L = REGIONPROPS_LABEL_IMAGE(BW,I,PROPERTY,LOGARITHM) returns matrix L
            %   whithout calling the regionprops function.
            %   
            %   Input: 
            %   - BW: binary image
            %   - I: intensity image, if you don't want to measure intensities provide
            %     empty matrix [] as second input
            %   - PROPERTY: string, e.g. 'Area', 'Eccentricity', 'MeanIntensity', etc.
            %     or matrix (when properties were already calculated)
            %   - LOGARITHM (optional): string, either 'two' for log2, 'ten' for log10,
            %     or 'nat' for log
            % 
            %   Output:
            %   IMLABEL: label image containing labels of the measured property.
            %   (Optionally, output is given in logarithmic form.)

            if isempty(imIntensity)
                imIntensity = zeros(size(imLogical));
            end

            if nargin == 3
                useLog = false;
            elseif nargin == 4
                useLog = true;
            end

            if ischar(Property)
                matProperty = cell2mat(struct2cell(regionprops(imLogical,imIntensity,Property)))';
            elseif ismatrix(Property)
                matProperty = Property;
            end
            imLabel = bwlabel(imLogical);
            Index = unique(imLabel);
            Index(Index==0) = [];
            for t = 1:length(Index)
                if useLog
                    if strcmp(logarithm,'two')
                        imLabel(imLabel==Index(t)) = log2(matProperty(t));
                    elseif strcmp(logarithm,'ten')
                        imLabel(imLabel==Index(t)) = log10(matProperty(t));
                    elseif strcmp(logarithm,'nat')
                        imLabel(imLabel==Index(t)) = log(matProperty(t));
                    end
                else
                    imLabel(imLabel==Index(t)) = matProperty(t);
                end
            end

        end

    end

end
