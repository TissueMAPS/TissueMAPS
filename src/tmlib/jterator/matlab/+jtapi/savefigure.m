function savefigure(fig, figure_file, file_type)
    % Writing figure instance to file
    % (using the `export_fig <https://github.com/altmany/export_fig>`_ package).
    % 
    % Parameters
    % ----------
    % fig: matlab.ui.Figure
    %     figure instance
    % figure_file: char
    %     name of the figure file
    % file_type: char, optional
    %     type of `figure_file` (e.g. "png" or "pdf")

    if nargin < 3
        file_type = 'pdf';
    end

    if ~ismember(file_type, ['png', 'pdf'])
        error('File type not supported.')
    end

    % export_fig requires the suffix to match the file type
    set(fig, 'PaperPosition', [0 0 5 5], 'PaperSize', [5 5]);
    figure_file = regexprep(figure_file, '\.\w+$', sprintf('.%s', file_type))
    export_fig(fig, figure_file, '-transparent');

end
