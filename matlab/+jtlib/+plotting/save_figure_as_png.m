function save_figure_as_png(fig, figure_file)
    % Write Matlab figure instance to file
    % (using the `export_fig <https://github.com/altmany/export_fig>`_ package).
    % 
    % Parameters
    % ----------
    % fig: matlab.ui.Figure
    %     figure instance
    % figure_file: char
    %     name of the figure file

    % export_fig requires the suffix to match the file type
    set(fig, 'PaperPosition', [0 0 5 5], 'PaperSize', [5 5]);
    figure_file = regexprep(figure_file, '\.\w+$', sprintf('.%s', 'png'));
    export_fig(fig, figure_file, '-transparent');

end
