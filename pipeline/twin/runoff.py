"""Daily surface runoff, SCS curve-number method (USDA NRCS; CLAUDE.md "Runoff"), in millimetres:
S = 25400 / CN - 254, Ia = 0.2 S, Q = (P - Ia)^2 / (P - Ia + S) when P > Ia, else 0.
Curve numbers by cover and soil group come from config/rules.yaml with their table source. Pure."""


def scs_runoff_mm(p_mm, cn):
    if cn >= 100:
        return float(p_mm)
    s = 25400.0 / cn - 254.0
    ia = 0.2 * s
    if p_mm <= ia:
        return 0.0
    return (p_mm - ia) ** 2 / (p_mm - ia + s)
