"""Harvest as a percentage of the field's potential (golden rule 11: never tonnes). FAO-33 yield
response, as in FAO-56 eq. 90: (1 - Ya/Ym) = Ky (1 - ETa/ETc), over the crop season, clamped 0..100.

Ky per crop comes from config/crops.json with its source. A crop with no published seasonal Ky carries
the owner-assumed neutral Ky 1.0 (`ky_assumed: true`, owner 2026-11-12), so it does get a harvest number,
labelled "assumed" wherever it is shown. Only a crop whose ky is null in crops.json (neither published nor
assumed) gets no harvest number; asking for one raises.

The clamp to 0..100 lets FAO-33's linear Ky relation run over the whole range of relative water use, from
ETa/ETc = 1 down to the deficit that gives 0%. FAO-33 derived the relation for a limited range of water
deficit (the published range: TODO-VERIFY in FAO-33 / FAO-66), so harvest numbers for very dry seasons
are an extrapolation of a straight line, not a measured response. Pure."""


def harvest_pct(sum_eta_mm, sum_etc_mm, ky):
    if ky is None:
        raise ValueError("Ky is null for this crop in crops.json (neither published nor owner-assumed): "
                         "no harvest number")
    import math
    if not (math.isfinite(sum_eta_mm) and math.isfinite(sum_etc_mm) and math.isfinite(ky)):
        raise ValueError(f"harvest needs finite ETa, ETc and Ky (got {sum_eta_mm}, {sum_etc_mm}, {ky})")
    if sum_etc_mm <= 0:
        return 100.0
    return float(min(100.0, max(0.0, 100.0 * (1.0 - ky * (1.0 - sum_eta_mm / sum_etc_mm)))))
