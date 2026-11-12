"""Reference evapotranspiration, FAO-56 Penman-Monteith, daily time step, soil heat flux G = 0.

Source: Allen, R.G., Pereira, L.S., Raes, D., Smith, M. (1998). Crop evapotranspiration: guidelines for
computing crop water requirements. FAO Irrigation and Drainage Paper 56. Equation numbers below are
FAO-56's (Chapter 3: https://www.fao.org/4/x0490e/x0490e07.htm; eq. 6 in Chapter 2). Worked examples
2, 8 and 18 are reproduced in tests/test_et0.py. Pure functions: numbers or numpy/pandas arrays in, numpy arrays (or floats) out.

One addition to FAO-56: in eq. 39, Rs/Rso is limited to 0.3..1.0. FAO-56 states only the upper limit;
below about 0.26 the cloudiness factor (1.35 Rs/Rso - 0.35) turns negative. The 0.3 floor is from the
ASCE-EWRI (2005) standardized reference-ET equation, Task Committee final report, eq. 18, p. 20 ("limited to
0.3 <= Rs/Rso <= 1.0"; citation in CREDITS.md and rules.yaml et0.rs_rso_limits), and matches pyet.
"""
import numpy as np

SIGMA = 4.903e-9      # Stefan-Boltzmann, MJ K-4 m-2 day-1 (eq. 39)
GSC = 0.0820          # solar constant, MJ m-2 min-1 (eq. 21)
ALBEDO = 0.23         # grass reference crop (eq. 38)
KELVIN = 273.16       # eq. 39 uses T + 273.16


def _a(x):
    return np.asarray(x, dtype=float)


def _out(x):
    return float(x) if np.ndim(x) == 0 else x


def pressure_kpa(z_m):                                   # eq. 7
    return _out(101.3 * ((293.0 - 0.0065 * _a(z_m)) / 293.0) ** 5.26)


def psychrometric_kpa_c(p_kpa):                          # eq. 8
    return _out(0.000665 * _a(p_kpa))


def e0_kpa(t_c):                                         # eq. 11
    t = _a(t_c)
    return _out(0.6108 * np.exp(17.27 * t / (t + 237.3)))


def es_kpa(tmax_c, tmin_c):                              # eq. 12
    return _out((_a(e0_kpa(tmax_c)) + _a(e0_kpa(tmin_c))) / 2.0)


def ea_from_rhmean_kpa(rh_pct, tmax_c, tmin_c):          # eq. 19
    return _out(_a(rh_pct) / 100.0 * _a(es_kpa(tmax_c, tmin_c)))


def delta_kpa_c(t_c):                                    # eq. 13
    t = _a(t_c)
    return _out(4098.0 * _a(e0_kpa(t)) / (t + 237.3) ** 2)


def ra_parts(lat_deg, doy):                              # eqs. 23-25: dr, solar declination, sunset hour angle
    phi = np.deg2rad(_a(lat_deg))
    j = _a(doy)
    dr = 1.0 + 0.033 * np.cos(2.0 * np.pi * j / 365.0)                 # eq. 23
    dec = 0.409 * np.sin(2.0 * np.pi * j / 365.0 - 1.39)               # eq. 24
    ws = np.arccos(np.clip(-np.tan(phi) * np.tan(dec), -1.0, 1.0))     # eq. 25
    return _out(dr), _out(dec), _out(ws)


def ra_mj_m2_day(lat_deg, doy):                          # eq. 21
    phi = np.deg2rad(_a(lat_deg))
    dr, dec, ws = (_a(v) for v in ra_parts(lat_deg, doy))
    ra = (24.0 * 60.0 / np.pi) * GSC * dr * (ws * np.sin(phi) * np.sin(dec) + np.cos(phi) * np.cos(dec) * np.sin(ws))
    return _out(ra)


def rso_mj_m2_day(ra, z_m):                              # eq. 37
    return _out((0.75 + 2e-5 * _a(z_m)) * _a(ra))


def rnl_mj_m2_day(tmax_c, tmin_c, ea_kpa, rs, rso):      # eq. 39 (Rs/Rso limited to 0.3..1.0, see top)
    ratio = np.clip(_a(rs) / _a(rso), 0.3, 1.0)
    t4 = ((_a(tmax_c) + KELVIN) ** 4 + (_a(tmin_c) + KELVIN) ** 4) / 2.0
    return _out(SIGMA * t4 * (0.34 - 0.14 * np.sqrt(_a(ea_kpa))) * (1.35 * ratio - 0.35))


def rn_mj_m2_day(rs, rnl, albedo=ALBEDO):                # eqs. 38, 40
    return _out((1.0 - albedo) * _a(rs) - _a(rnl))


def et0_mm(tmax_c, tmin_c, u2_ms, rs_mj_m2_day, z_m, lat_deg, doy, rh_mean=None, ea=None):
    """FAO-56 eq. 6 with G = 0. Give either rh_mean (percent, eq. 19) or ea (kPa)."""
    if ea is None:
        if rh_mean is None:
            raise ValueError("et0_mm needs rh_mean or ea")
        ea = ea_from_rhmean_kpa(rh_mean, tmax_c, tmin_c)
    tmax, tmin, u2, rs, ea = _a(tmax_c), _a(tmin_c), _a(u2_ms), _a(rs_mj_m2_day), _a(ea)
    t = (tmax + tmin) / 2.0
    d = _a(delta_kpa_c(t))
    g = _a(psychrometric_kpa_c(pressure_kpa(z_m)))
    es = _a(es_kpa(tmax, tmin))
    ra = _a(ra_mj_m2_day(lat_deg, doy))
    rnl = _a(rnl_mj_m2_day(tmax, tmin, ea, rs, rso_mj_m2_day(ra, z_m)))
    rn = _a(rn_mj_m2_day(rs, rnl))
    num = 0.408 * d * rn + g * (900.0 / (t + 273.0)) * u2 * (es - ea)
    den = d + g * (1.0 + 0.34 * u2)
    return _out(num / den)
