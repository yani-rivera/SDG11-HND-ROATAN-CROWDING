"""Tanaka (illuminated contour) rendering of the people-density surface — static posters.

Same recipe as the page's Tanaka view:
  density = people per km² of land (residents + cruise visitors), Gaussian-smoothed
  fill    = banded by density, hue from the resident colour to the visitor colour by visitor share
  lines   = contour edges lit on the side facing the light, dark on the side facing away
"""

import math

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.patches import PathPatch
from matplotlib.path import Path
from matplotlib.colors import to_rgb
from matplotlib.transforms import Affine2D

from . import grid as G


def visitors_for(data, ships=0, month=None):
    feats = data["hexes"]["features"]
    n_t = len(data["terminals"])
    if month is not None:
        m = month
        return np.array([sum(f["properties"]["share"][t] * m["passengers"][t] / m["days"]
                             for t in range(n_t)) for f in feats])
    cap = data["ships"]["default_capacity"]
    return np.array([sum(cap * f["properties"]["share"][s % n_t] for s in range(ships))
                     for f in feats])


def surfaces(data, vis):
    feats = data["hexes"]["features"]
    res = np.array([f["properties"]["res"] for f in feats])
    land = np.array([f["properties"]["land_km2"] for f in feats])
    g = data["grid"]
    grid = {**g, "idx": np.asarray(g["idx"])}
    sigma = data["tanaka"]["blur_sigma_cells"]
    tot = G.gaussian_blur(G.density(grid, res + vis, land), sigma)
    vd = G.gaussian_blur(G.density(grid, vis, land), sigma)
    share = np.divide(vd, tot, out=np.zeros_like(tot), where=tot > 1e-9)
    return tot, share


def fill_rgba(tot, share, data):
    c, tk = data["colours"], data["tanaka"]
    thr = np.asarray(tk["thresholds_per_km2"])
    level = np.digitize(tot, thr)                       # 0 = below the first contour
    t = level / len(thr)
    mix = np.clip(share / tk["share_full_coral"], 0, 1)[..., None]
    hue = (1 - mix) * np.array(to_rgb(c["residents"])) + mix * np.array(to_rgb(c["visitors"]))
    low = np.array(to_rgb(c["tanaka_low"]))
    k = (0.25 + 0.75 * t)[..., None]
    rgb = (1 - k) * low + k * hue
    alpha = (level > 0).astype(float)[..., None]
    return np.concatenate([rgb, alpha], axis=-1)


def _sample(arr, gx, gy):
    h, w = arr.shape
    i = int(min(max(round(gy - 0.5), 0), h - 1))
    j = int(min(max(round(gx - 0.5), 0), w - 1))
    return arr[i, j]


def land_patch(polys, transform):
    """Island shape as a clip path (keeps the smoothed surface off the sea)."""
    verts, codes = [], []
    for poly in polys:
        for ring in poly:
            r = np.asarray(ring)
            verts += r.tolist() + [r[0].tolist()]
            codes += [Path.MOVETO] + [Path.LINETO] * (len(r) - 1) + [Path.CLOSEPOLY]
    return PathPatch(Path(verts, codes), transform=transform, fc="none", ec="none")


def tanaka_lines(ax, tot, data, transform, clip=None):
    g, c, tk = data["grid"], data["colours"], data["tanaka"]
    west, north, dlon, dlat = g["west"], g["north"], g["dlon"], g["dlat"]
    xs = west + (np.arange(g["width"]) + 0.5) * dlon
    ys = north - (np.arange(g["height"]) + 0.5) * dlat
    cs = ax.contour(xs, ys, tot, levels=tk["thresholds_per_km2"], alpha=0)
    az = math.radians(tk["light_azimuth_deg"])
    L = np.array([math.sin(az), math.cos(az)])          # unit vector towards the light
    light, shadow = np.array(to_rgb(c["tanaka_light"])), np.array(to_rgb(c["tanaka_shadow"]))
    segs, cols = [], []
    for level_segs in cs.allsegs:
        for line in level_segs:
            for (x0, y0), (x1, y1) in zip(line[:-1], line[1:]):
                dx, dy = (x1 - x0) / dlon, (y1 - y0) / dlat   # in grid cells (≈ metres)
                ln = math.hypot(dx, dy)
                if ln == 0:
                    continue
                nx, ny = dy / ln, -dx / ln                     # a normal (east/north units)
                mx, my = (x0 + x1) / 2, (y0 + y1) / 2
                gx, gy = (mx - west) / dlon + nx * 0.5, (north - my) / dlat - ny * 0.5
                if _sample(tot, gx, gy) > _sample(tot, gx - nx, gy + ny):
                    nx, ny = -nx, -ny                          # make it point downhill
                s = (nx * L[0] + ny * L[1] + 1) / 2
                segs.append([(x0, y0), (x1, y1)])
                cols.append(shadow + (light - shadow) * s)
    lc = LineCollection(segs, colors=cols, linewidths=tk["line_width"] * 0.6,
                        capstyle="round", transform=transform)
    ax.add_collection(lc)
    if clip is not None:
        lc.set_clip_path(clip)


def poster(data, pcfg, out_png):
    c = data["colours"]
    months = {f"{m['year']}-{m['month']:02d}": m for m in data["months"]}
    g = data["grid"]
    extent = [g["west"], g["west"] + g["width"] * g["dlon"],
              g["north"] - g["height"] * g["dlat"], g["north"]]
    lat0 = (extent[2] + extent[3]) / 2
    lon0 = (extent[0] + extent[1]) / 2
    kx = math.cos(math.radians(lat0))
    rot = float(pcfg.get("rotation_deg", 0))
    panels = pcfg["panels"]

    # lon/lat -> equal-scale local units, then rotate so the island lies horizontally
    def make_tr(ax):
        return (Affine2D().translate(-lon0, -lat0).scale(kx, 1.0).rotate_deg(rot)
                + ax.transData)
    corners = np.array([[extent[0], extent[2]], [extent[1], extent[2]],
                        [extent[1], extent[3]], [extent[0], extent[3]]])
    loc = Affine2D().translate(-lon0, -lat0).scale(kx, 1.0).rotate_deg(rot).transform(corners)
    land_geom = data["land"]["geometry"]
    polys = land_geom["coordinates"] if land_geom["type"] == "MultiPolygon" else [land_geom["coordinates"]]
    land_pts = np.vstack([np.asarray(pl[0]) for pl in polys])
    lp = Affine2D().translate(-lon0, -lat0).scale(kx, 1.0).rotate_deg(rot).transform(land_pts)
    pad = 0.01
    xlim = (lp[:, 0].min() - pad, lp[:, 0].max() + pad)
    ylim = (lp[:, 1].min() - pad, lp[:, 1].max() + pad)
    aspect = (ylim[1] - ylim[0]) / (xlim[1] - xlim[0])

    panel_w = 0.94
    fig_w = 12.0
    panel_h_in = fig_w * panel_w * aspect
    fig_h = panel_h_in * 1.35 * len(panels) + 2.6
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor=c["sea"])
    head, foot = 1.5 / fig_h, 1.1 / fig_h
    fig.text(0.04, 1 - 0.35 / fig_h, pcfg["title"], fontsize=24, weight="bold",
             color=c["tanaka_shadow"], va="top")
    fig.text(0.04, 1 - 0.95 / fig_h, pcfg["subtitle"], fontsize=11, color="#4a5a66", va="top")
    slot = (1 - head - foot) / len(panels)
    ph = panel_h_in / fig_h

    for k, p in enumerate(panels):
        m = months.get(p["month"]) if p.get("month") else None
        if p.get("month") and m is None:
            raise ValueError(f"Poster panel month {p['month']} is not in the cruise data.")
        vis = visitors_for(data, p.get("ships", 0), m)
        tot, share = surfaces(data, vis)
        y0 = 1 - head - (k + 1) * slot
        ax = fig.add_axes([0.03, y0, panel_w, ph])
        ax.set_facecolor(c["sea"])
        tr = make_tr(ax)
        for poly in polys:
            xy = np.asarray(poly[0])
            ax.fill(xy[:, 0], xy[:, 1], color=c["land"], ec=c["land_outline"], lw=0.4,
                    zorder=0, transform=tr)
        im = ax.imshow(fill_rgba(tot, share, data), extent=extent, origin="upper",
                       interpolation="bilinear", zorder=1)
        im.set_transform(tr)
        clip = None
        if data["tanaka"].get("clip_to_land", False):
            clip = land_patch(polys, tr)
            ax.add_patch(clip)
            im.set_clip_path(clip)
        tanaka_lines(ax, tot, data, tr, clip)
        for t in data["terminals"]:
            ax.plot(t["lon"], t["lat"], "o", ms=5, mfc="white", mec=c["tanaka_shadow"],
                    zorder=5, transform=tr)
        ax.set_xlim(*xlim); ax.set_ylim(*ylim)
        ax.set_aspect("equal")
        ax.set_axis_off()
        vt = vis.sum()
        stat = ("no cruise visitors" if vt < 1 else
                f"{vt:,.0f} cruise visitors · {vt / data['residents_total'] * 100:.1f} per 100 residents")
        gap = slot - ph
        fig.text(0.04, y0 + ph + 0.55 * gap, p["label"], fontsize=14, weight="bold",
                 color=c["tanaka_shadow"], va="bottom")
        fig.text(0.04, y0 + ph + 0.12 * gap, stat, fontsize=10, color="#4a5a66", va="bottom")
    # north arrow in its own small box (top right), rotated with the map
    na = fig.add_axes([0.89, 1 - 1.45 / fig_h, 0.07, 1.1 / fig_h])
    na.set_xlim(-1, 1); na.set_ylim(-1, 1); na.set_aspect("equal"); na.set_axis_off()
    a = math.radians(rot)
    nx, ny = -math.sin(a), math.cos(a)                 # (0, 1) rotated by rot degrees
    na.annotate("", xy=(nx * 0.6, ny * 0.6), xytext=(-nx * 0.6, -ny * 0.6),
                arrowprops=dict(arrowstyle="-|>", color=c["tanaka_shadow"], lw=1.4))
    na.text(nx * 0.9, ny * 0.9, "N", ha="center", va="center", fontsize=10,
            color=c["tanaka_shadow"], weight="bold")

    # legend: hue by visitor share (bottom right)
    lx = fig.add_axes([0.66, 0.55 * foot, 0.28, 0.12 * foot])
    ramp = np.linspace(0, 1, 100)
    rgb = [(1 - r) * np.array(to_rgb(c["residents"])) + r * np.array(to_rgb(c["visitors"])) for r in ramp]
    lx.imshow([rgb], aspect="auto", extent=[0, 1, 0, 1]); lx.set_yticks([])
    lx.set_xticks([0, 1]); lx.set_xticklabels(["mostly residents", "mostly cruise visitors"], fontsize=8)
    for sp in lx.spines.values():
        sp.set_visible(False)
    thr = data["tanaka"]["thresholds_per_km2"]
    placed = ("Residents placed with GHS-POP 2025 (EU JRC), scaled to "
              f"{data['residents_total']:,.0f}; modelled until the 2026 census."
              if data["residents_mode"] == "population_raster"
              else "Residents spread by land area (placeholder).")
    lines = [f"Contours at {thr[0]:,}–{thr[-1]:,} people/km², same levels in every panel.",
             data.get("scope_note", ""),
             "Sources: INE 2018 projection; GHS-POP 2025 (EU JRC); Instituto Hondureño de Turismo cruise records;",
             "SINIT/OCHA HDX outline. " + placed]
    fig.text(0.04, 0.3 * foot, "\n".join(l for l in lines if l), fontsize=7.5, color="#4a5a66",
             va="bottom", linespacing=1.5)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=pcfg["dpi"], facecolor=fig.get_facecolor())
    plt.close(fig)
