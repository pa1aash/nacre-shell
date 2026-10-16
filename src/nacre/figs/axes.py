"""Axis helpers shared by the templates."""
from matplotlib.ticker import FuncFormatter, LogLocator, NullFormatter


def log_axis(axis, subs=(1.0, 2.0, 5.0)):
    """Log-scale tick labels in plain numbers at 1-2-5 steps; minor ticks unlabelled.

    axis: ax.xaxis or ax.yaxis of an axes already set to a log scale.
    """
    axis.set_major_locator(LogLocator(base=10.0, subs=subs))
    axis.set_major_formatter(FuncFormatter(lambda v, _pos: "%g" % v))
    axis.set_minor_formatter(NullFormatter())
