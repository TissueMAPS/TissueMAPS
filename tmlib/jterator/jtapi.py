import mpld3
from bokeh.resources import CDN
from bokeh.embed import file_html
from bokeh.plotting import save
import logging

logger = logging.getLogger(__name__)


def save_mpl_figure(fig, figure_file):
    '''
    Writing figure instance to file as HTML string with embedded javascript
    code using the `mpld3 <http://mpld3.github.io/>`_ library.

    Parameters
    ----------
    fig: matplotlib.figure.Figure
        figure instance
    figure_file: str
        name of the figure file

    Note
    ----
    Display of the figure in the browser requires internet connection.
    See `troubleshooting <http://mpld3.github.io/faq.html#troubleshooting>`_.
    '''
    mousepos = mpld3.plugins.MousePosition(fontsize=20)
    mpld3.plugins.connect(fig, mousepos)
    logger.debug('write figure to HTML file: "%s"' % figure_file)
    mpld3.save_html(fig, figure_file)   # template_type='simple'


def save_bokeh_figure(fig, figure_file):
    '''
    Writing figure instance to file as HTML string with embedded javascript
    code using the `bokeh <http://bokeh.pydata.org/en/latest/>`_ library.

    Parameters
    ----------
    fig: bokeh.plotting.Figure
        figure instance
    figure_file: str
        name of the figure file
    '''
    # save(obj=fig, filename=figure_file)
    html = file_html(fig, CDN, "jterator plot")
    with open(figure_file, 'w') as f:
        f.write(html)
