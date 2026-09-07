import sys, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.addons.drawing.config import Configuration, ColorPolicy

src, out = sys.argv[1], sys.argv[2]
doc = ezdxf.readfile(src)
fig = plt.figure(figsize=(16.5, 11.7), dpi=140)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_axis_off()
ctx = RenderContext(doc)
cfg = Configuration(color_policy=ColorPolicy.BLACK, background_policy=None) \
      if hasattr(Configuration, "color_policy") else Configuration()
try:
    Frontend(ctx, MatplotlibBackend(ax), config=cfg).draw_layout(doc.modelspace(), finalize=True)
except TypeError:
    Frontend(ctx, MatplotlibBackend(ax)).draw_layout(doc.modelspace(), finalize=True)
fig.savefig(out, facecolor="white", dpi=140)
print("wrote", out)
