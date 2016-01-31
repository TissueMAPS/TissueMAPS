using Gadfly
using Plotly


function jtfigure(fig, filename, fig_format)
    if fig_format == 'pdf'
        draw(PDF(@sprintf("%s.pdf", filename), 6inch, 6inch), fig)
    elseif fig_format == 'plotly'
        # figure_url = Plotly.plot(fig, filename=filename)
        # return figure_url
    end
end
