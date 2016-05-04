
# Created on 25-March-2016 by Dr. Saadia Iftikhar, saadia.iftikhar@fmi.ch
# ---------------------------------------------------------------------

import matplotlib.pyplot as plt
def save_figure_as_png(fig=None,figure_file=None,*args,**kwargs):
       plt.savefig(figure_file, bbox_inches='tight')
return
