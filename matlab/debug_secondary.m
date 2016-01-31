directory = '/Users/mdh/Desktop/tmp';
image_filename = 'test.tiff';
image_file = fullfile(directory, image_filename);
image = uint16(imread(image_file));

input_image = double(image) ./ 2^16;
correction_factors = [2, 1.5, 1.3, 0.9, 0.7, 0.6, 0.58, 0.55, 0.50, 0.45, 0.4, 0.35, 0.3, 0.25];
min_treshold = 0;
max_treshold = 1;

mask_filename = 'nuclei.png';
mask_file = fullfile(directory, mask_filename);
mask = imread(mask_file);

import jtlib.*;
out = jtlib.segmentSecondary(input_image, mask, mask, correction_factors, min_treshold, max_treshold);