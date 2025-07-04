"""Example script that demonstrates under/overflow bins."""

from __future__ import annotations

import numpy as np

from puma import Histogram, HistogramPlot

rng = np.random.default_rng(42)

vals = rng.normal(size=10_000)

plot_without = HistogramPlot()
plot_without.title = "Without underflow/overflow bins"
plot_without.add(
    Histogram(
        values=vals,
        bins=40,
        bins_range=(-2, 2),
        underoverflow=False,
        label="Gaussian($\\mu=0$, $\\sigma=1$)",
    )
)
plot_without.draw()
plot_without.savefig("hist_without_underoverflow.png")

plot_with = HistogramPlot()
plot_with.title = "With underflow/overflow bins"
plot_with.add(
    Histogram(
        values=vals,
        bins=40,
        bins_range=(-2, 2),
        label="Gaussian($\\mu=0$, $\\sigma=1$)",
    )
)
plot_with.draw()
plot_with.savefig("hist_with_underoverflow.png")
