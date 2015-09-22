function writedata(data, data_file)
    % Writing data to HDF5 file.
    % 
    % For each key, value pair the key will define the name of the dataset
    % and the value will be stored as the actual dataset.
    % 
    % Parameters
    % ----------
    % data: structure array
    %     data that should be saved
    % data_file: char
    %     path to the data file

    import h5.*;

    hdf5_filename = data_file;

    % Works for strings, numbers, matrices and cell array of strings.
    % One could also implement structure arrays -> "Compound"
    % and cell arrays of matrices -> "Variable Length",
    % but it gets pretty complicates then.
    % For examples see:
    % http://www.hdfgroup.org/ftp/HDF5/examples/examples-by-api/api18-m.html

    fid = H5F.open(hdf5_filename, 'H5F_ACC_RDWR','H5P_DEFAULT');

    keys = fieldnames(data);
    for i = 1:length(keys)
        key = keys{i};
        hdf5_location = key;
        value = data.(key);
        h5datacreate(fid, hdf5_location, ...
                     'type', class(value), 'size', size(value)');
        h5varput(fid, hdf5_location, value');
        fprintf(sprintf('jt -- %s: wrote dataset ''%s'' to HDF5 location: "%s"\n', ...
                        mfilename, key, hdf5_location));
    end

    H5F.close(fid);
end
