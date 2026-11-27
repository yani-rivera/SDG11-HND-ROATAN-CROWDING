"""Cruise calls per terminal and month from the tourism institute records.

One row of the source = one ship call (ship, month, port, passengers).
Port names and month names are mapped through catalogs, never hard-coded.
"""

import calendar

import pandas as pd


def load(xlsx_path, ccfg: dict, terminals: pd.DataFrame, months_catalog):
    cols = ccfg["columns"]
    raw = pd.read_excel(xlsx_path, sheet_name=ccfg.get("sheet", 0))
    months = pd.read_csv(months_catalog, encoding="utf-8-sig")
    month_num = dict(zip(months["month_name"].str.strip(), months["month"]))

    port_to_t = {str(p).strip(): i for i, p in enumerate(terminals["source_port"])}
    df = raw.rename(columns={cols["year"]: "year", cols["month"]: "month_name",
                             cols["port"]: "port", cols["passengers"]: "passengers",
                             cols["ship"]: "ship"})
    report = {"rows_total": int(len(df))}

    empty = df["port"].isna() & (df["passengers"].fillna(0) == 0)
    report["rows_dropped_empty"] = int(empty.sum())
    df = df[~empty]
    other = ~df["port"].astype(str).str.strip().isin(port_to_t)
    report["rows_other_ports"] = int(other.sum())
    df = df[~other].copy()
    dup = df.drop(columns=[c for c in ("row_number",) if c in df]).duplicated(keep=False)
    report["rows_exact_duplicates_kept"] = int(dup.sum())

    df["month_name"] = df["month_name"].astype(str).str.strip()
    unknown = sorted(set(df["month_name"]) - set(month_num))
    if unknown:
        raise ValueError(f"Month names not in the months catalog: {unknown}")
    df["month"] = df["month_name"].map(month_num).astype(int)
    df["terminal"] = df["port"].astype(str).str.strip().map(port_to_t)

    monthly = (df.groupby(["year", "month", "terminal"])
                 .agg(passengers=("passengers", "sum"), calls=("passengers", "size"))
                 .reset_index())
    report["passengers_by_year"] = {int(k): int(v) for k, v in
                                    df.groupby("year")["passengers"].sum().items()}
    ship_median = {int(k): int(round(v)) for k, v in
                   df.groupby("year")["passengers"].median().items()}
    biggest = df.loc[df["passengers"].idxmax()]
    return df, monthly, report, ship_median, {"ship": str(biggest["ship"]),
                                              "passengers": int(biggest["passengers"])}


def web_months(monthly: pd.DataFrame, n_terminals: int, months_catalog):
    """List of {year, month, label, days, passengers[t], calls[t]} in calendar order."""
    months = pd.read_csv(months_catalog, encoding="utf-8-sig")
    label = dict(zip(months["month"], months["label"]))
    out = []
    for (y, m), grp in monthly.groupby(["year", "month"]):
        p, c = [0] * n_terminals, [0] * n_terminals
        for r in grp.itertuples():
            p[int(r.terminal)] = int(r.passengers)
            c[int(r.terminal)] = int(r.calls)
        out.append({"year": int(y), "month": int(m), "label": f"{label[m]} {y}",
                    "days": calendar.monthrange(int(y), int(m))[1],
                    "passengers": p, "calls": c})
    return out
