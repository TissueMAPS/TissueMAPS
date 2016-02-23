function save_plotly_figure(fig, figure_file)
    % Write `plotly <https://plot.ly/python/>`_ figure instance to
    % file as HTML string with embedded javascript code.
    % 
    % Parameters
    % ----------
    % fig: plotly.graph_objs.Figure or plotly.graph_objs.Data
    %     figure instance
    % figure_file: str
    %     name of the figure file

    fig.layout.width = 800;
    fig.layout.height = 800;
    % Unfortunately, one cannot just pass the absolute path to the file
    % but only the name. The file will then automatically be written into
    % the current working directory.
    [folder, filename, extension] = fileparts(figure_file);
    fig.PlotOptions.FileName = filename;
    current_dir = pwd;
    cd(folder);
    html_file = plotlyoffline(fig);
    cd(current_dir);

end
