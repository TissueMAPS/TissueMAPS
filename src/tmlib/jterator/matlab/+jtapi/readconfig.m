function config = readconfig(configuration)
    % Reading configuration settings from YAML string.
    % 
    % Parameters
    % ----------
    % configuration: char
    %     configuration settings
    %
    % Returns
    % -------
    % structure array

    import yaml.*;

    config = yaml.ReadYaml(configuration, 0, 0, 1);
    fprintf('jt -- %s: read configuration settings from "%s"', ...
            mfilename, configuration)
end
