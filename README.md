# SDG11-HND-ROATAN-CROWDING — "An Island That Makes Room"

An interactive 3D hexagon map of Roatán. Each hexagon is a tower: **residents** (teal) at the base
and **cruise visitors** (coral) stacked on top.
- **Scenarios:** *Just us · 1 · 2 · 3 ships*, with a passengers-per-ship slider. The default is the
  median passengers per call in the latest year of data (3,928 in 2025).
- **Real data:** "an average day in <month>", computed as each terminal's passengers that month
  divided by the days in the month, from the tourism institute's cruise records (one row = one ship
  call, 2021–2025).

## What's real and what's modelled — read this first
**Real data**
- **Cruise calls and passengers:** Instituto Hondureño de Turismo records captured from its public
  report, 1,808 ship calls in 2021–2025, by terminal and month. The yearly totals match the source.
- **Island outline:** Islas de la Bahía department polygon, SINIT 2016 via OCHA HDX (cod-ab-hnd).
- **Residents total:** 61,032, INE 2018 projection for Roatán + José Santos Guardiola.
- **Where residents live:** GHS-POP 2025 (EU Joint Research Centre, R2023A, 3 arc-seconds ≈ 90 m,
  tile R8_C10, CC BY 4.0). It is itself a **model** (census counts spread onto built-up areas seen
  from space), not a count. It's used until the 2026 census is published.
- **Terminal locations:** from public sources and checked against the coastline (see the
  `note` column in `catalogs/cruise_terminals.csv`):
  - Isla Tropicale: Waymarking WMAEC1 (N16°19.614 W086°29.844), which agrees with MarineLink within
    about 60 m.
  - Town Center: PredictWind / MarineLink (port code HNRTB), about 60 m off shore at the pier. These
    two may share one underlying source.
- **Spending per passenger:** BREA/FCCA 2024 survey (see "Economy line" below).

**Modelled / assumed (stated on the page too)**
- **Residents' total vs. the grid:** GHS-POP puts about 81,500 people inside the island hexagons
  (about 76,900 inside the SINIT outline). That's well above the INE 2018 projection, which fits
  growth since 2018 and the user's own doubts about census coverage. With `scale_to_total: true`
  (the default) GHS-POP decides **where** people live and INE decides **how many**. Set it to
  `false` to keep the GHS-POP total instead. The ratios in the panel change with that choice.
- **Where visitors go:** the per-terminal spread (share staying close, fade distance, cutoff) is an
  educated guess based on how each terminal works. It is **not measured**. Data on where passengers
  actually go (excursions, mobile data, counts at beaches and town) would replace it.
- **The 1 / 2 / 3 ship buttons are illustrative scenarios.** The month menu uses the real data.
- **"Average day"** is a monthly total divided by the days in the month. There are no daily dates,
  so peak days are not shown.
- **Time mismatch:** a 2018 resident projection is set against 2021–2025 passengers. The real 2025
  population is probably higher, so visitor ratios are an upper bound until the 2026 census.
- **Cruise visitors only:** no air or ferry arrivals (see "Scope" below).

So the **amount** of cruise visitors is real data. **Where** residents live comes from the GHS-POP
model, and **where** visitors go is an assumption.

## Two views, plus posters
- **Towers:** 3D hexagons, with residents at the base and cruise visitors stacked on top.
- **Tanaka:** people per km² (residents + cruise visitors) as a smoothed surface with illuminated
  contours, lit from the northwest. The fill colour goes from the resident colour to the visitor
  colour by visitor share. The contour levels are fixed (`tanaka.thresholds_per_km2`), so every view
  is comparable. The contours are recalculated live in the browser with d3-contour (bundled locally).
- **Posters:** `scripts/make_posters.py` renders the panels in `posters.panels` (by default
  *Just us · Three ships · An average day, December 2025*) with the same recipe, rotated so the
  island lies horizontally (`posters.rotation_deg`), with a north arrow.

**All colours are in `config.yaml` under `colours:`:** residents, visitors, sea, land,
land_outline, tanaka_light, tanaka_shadow, tanaka_low. The page, the Tanaka view and the posters
all read them from there.

## Layout
```
config/config.yaml        settings (residents total, grid size, visitor assumptions, colours)
catalogs/                 cruise_terminals.csv (lat/lon with sources; source_port + per-terminal spread),
                          months_es.csv (Spanish month name -> number), visitor_destinations.csv (optional)
data/cruises/             cruises.xlsx (tourism institute records, one row per ship call)
data/outline/             Roatán outline: Islas de la Bahía (SINIT 2016, OCHA HDX cod-ab-hnd), clipped
data/population/          GHS-POP 2025 tile GHS_POP_E2025_GLOBE_R2023A_4326_3ss_V1_0_R8_C10.tif (not in the
                          zip because of its size; download from the JRC GHSL site and put it here)
scripts/build_hexes.py    builds docs/data/crowd_data.js + output/ (GPKG, CSV utf-8-sig, crowd_data.json, provenance.json)
scripts/make_posters.py   Tanaka posters -> output/posters/ (+ provenance_posters.json)
                          GeoJSON -> output/geojson/: hexes.geojson (residents, shares, vis_1..3_ships,
                          vis_YYYY_MM average days), terminals.geojson, contours_<panel>.geojson
scripts/crowd/            modules: config, inputs, hexgrid, residents, cruises, visitors, grid, tanaka, export, provenance
output/                   hexes GPKG/CSV, roatan_cruise_calls_by_month.csv (utf-8-sig), provenance.json
docs/                     the web page (GitHub Pages-ready). Bundled in docs/vendor with their licences:
                          MapLibre GL JS 4.7.1 (BSD-3), d3-contour 4.0.3 + d3-array 3.2.5 (ISC)
```

## Run
```
pip install -r requirements.txt
python scripts/build_hexes.py --config config/config.yaml
python scripts/make_posters.py --config config/config.yaml     # optional: posters
```
Then open `docs/index.html` in a browser. It works straight from disk; no server is needed.

The terminal coordinates are already filled in `catalogs/cruise_terminals.csv`. If a row's lat/lon
is ever left empty, the script stops with a message instead of guessing.

## Scope
**Cruise visitors only.** Tourists who arrive by air (Roatán airport) or by ferry (from La Ceiba) are
not in the data, so the real crowd on the island is larger than the map shows. The page says this
visibly under the legend. If air and ferry arrivals for Roatán become available, they could be added
as a third tower colour.

## Assumptions (also shown on the page)
- Residents: 61,032 (INE 2018 projection, Roatán + José Santos Guardiola), placed with GHS-POP 2025.
  Without a raster (`residents.raster: null`) they're spread by land area, and the page shows a
  placeholder note.
- Each terminal has its own spread settings in the catalog (educated guesses, not measured).
  Isla Tropicale (formerly Mahogany Bay, renamed in April 2026) is a Carnival Corp. private
  destination with its own beach islet, so most passengers stay close (85%, fading over about
  0.7 km, zero at 3 km). Town Center sits in Coxen Hole, so passengers spread
  further (60%, about 1.5 km, zero at 4 km). The remaining share goes to the visitor destinations in
  the catalog. If that catalog is empty, everyone stays around the terminals.
- The cruise data has monthly totals only, with no daily dates, so "average day" is a monthly mean,
  not a peak day.
- Data checks are recorded in provenance.json: six empty rows for Jan–Jun 2021 (COVID pause, no port)
  are dropped; 16 rows from other ports are filtered out; one exact duplicate pair (Viking Mars,
  Dec 2025, Puerto de Roatán, 875 passengers) is kept because it's part of the published total.
  Yearly totals match the source: 313,703 · 942,988 · 1,391,018 · 1,802,495 · 1,979,002.
- Ship 1 docks at the first terminal, ship 2 at the second, and ship 3 at the first again.
- Tower heights use one fixed scale across every view, so heights can be compared honestly.

## Economy line
The panel shows **estimated cruise spending** for the day shown, calculated as cruise visitors ×
US$99.20, always with its caveat and reference:
> Business Research and Economic Advisors (BREA) for the Florida-Caribbean Cruise Association (2024).
> *Economic Contribution of Cruise Tourism to the Destination Economies*, Vol. II — Honduras,
> 2023/2024 cruise year. https://f-cca.com/downloads/2024-Caribbean-Cruse-Analysis-Vol-II.pdf

The figure is self-reported spending from an industry-funded passenger survey. How much of it stays
on the island isn't measured, and the tourism institute's own estimate uses the same survey. The
study doesn't split spending by terminal. All of this text lives in `config.yaml` (`economy:`).

## Security & mobile
- No external requests at all. A strict Content-Security-Policy is set (scripts only from the
  site itself; workers only from blob:, which MapLibre needs).
- Text from the data is inserted with textContent only.
- On phones the panel becomes a bottom sheet, tap targets are at least 44 px, two-finger tilt and
  rotate work, and the animation respects reduced-motion settings.
