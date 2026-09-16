"""Lap time / tire degradation model.

Fits a single linear model to a race's clean pace laps:

    lap_time_s = intercept
               + driver_offset[driver]                     # car+driver pace delta
               + compound_offset[compound]                 # compound base pace delta
               + fuel_effect_per_lap * lap_number           # fuel burn-off (global, ~linear)
               + deg_linear[compound]  * tyre_life          # compound degradation, linear term
               + deg_quad[compound]    * tyre_life**2        # compound degradation, quadratic term
               + noise

`lap_number` (monotonic across the whole race) identifies the fuel effect,
while `tyre_life` (resets every stint) identifies degradation — the two are
only weakly correlated in real data because of pit stops, which is what
makes both separately estimable from a single-race OLS fit.

Fit with plain OLS (numpy.linalg.lstsq) rather than pulling in statsmodels —
the design matrix is just dummy variables plus two numeric columns, no need
for a heavier dependency.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PaceModel:
    intercept: float
    reference_driver: str
    reference_compound: str
    driver_offset: dict[str, float]
    compound_offset: dict[str, float]
    fuel_effect_per_lap: float
    deg_linear: dict[str, float]
    deg_quad: dict[str, float]
    residual_std: float
    n_laps_fit: int
    compounds: tuple[str, ...] = field(default_factory=tuple)

    def predict(self, *, driver: str, compound: str, tyre_life: float, lap_number: float) -> float:
        d_off = self.driver_offset.get(driver, 0.0)
        c_off = self.compound_offset.get(compound, 0.0)
        lin = self.deg_linear.get(compound, self.deg_linear.get(self.reference_compound, 0.0))
        quad = self.deg_quad.get(compound, self.deg_quad.get(self.reference_compound, 0.0))
        return (
            self.intercept
            + d_off
            + c_off
            + self.fuel_effect_per_lap * lap_number
            + lin * tyre_life
            + quad * tyre_life**2
        )

    def sample(
        self,
        *,
        driver: str,
        compound: str,
        tyre_life: float,
        lap_number: float,
        rng: np.random.Generator,
    ) -> float:
        """Predicted lap time plus Gaussian noise drawn from the fit's residual spread."""
        mean = self.predict(
            driver=driver, compound=compound, tyre_life=tyre_life, lap_number=lap_number
        )
        return float(mean + rng.normal(0.0, self.residual_std))


def fit_pace_model(pace_laps: pd.DataFrame, min_laps: int = 20) -> PaceModel:
    """Fit a PaceModel from a `clean_pace_laps`-shaped DataFrame.

    Expects columns: driver, compound, tyre_life, lap_number, lap_time_s.
    """
    if len(pace_laps) < min_laps:
        raise ValueError(
            f"Need at least {min_laps} clean pace laps to fit a pace model, got {len(pace_laps)}"
        )

    df = pace_laps.dropna(subset=["driver", "compound", "tyre_life", "lap_number", "lap_time_s"])

    drivers = sorted(df["driver"].unique())
    compounds = sorted(df["compound"].unique())
    reference_driver = drivers[0]
    # Prefer MEDIUM as the reference compound when present so offsets read intuitively.
    reference_compound = "MEDIUM" if "MEDIUM" in compounds else compounds[0]

    other_drivers = [d for d in drivers if d != reference_driver]
    other_compounds = [c for c in compounds if c != reference_compound]

    n = len(df)
    columns = (
        ["intercept", "lap_number"]
        + [f"driver:{d}" for d in other_drivers]
        + [f"compound:{c}" for c in other_compounds]
        + [f"deg_lin:{c}" for c in compounds]
        + [f"deg_quad:{c}" for c in compounds]
    )
    X = np.zeros((n, len(columns)), dtype=float)
    col_idx = {name: i for i, name in enumerate(columns)}

    lap_number = df["lap_number"].to_numpy(dtype=float)
    tyre_life = df["tyre_life"].to_numpy(dtype=float)
    driver_arr = df["driver"].to_numpy()
    compound_arr = df["compound"].to_numpy()

    X[:, col_idx["intercept"]] = 1.0
    X[:, col_idx["lap_number"]] = lap_number
    for d in other_drivers:
        X[driver_arr == d, col_idx[f"driver:{d}"]] = 1.0
    for c in other_compounds:
        X[compound_arr == c, col_idx[f"compound:{c}"]] = 1.0
    for c in compounds:
        mask = compound_arr == c
        X[mask, col_idx[f"deg_lin:{c}"]] = tyre_life[mask]
        X[mask, col_idx[f"deg_quad:{c}"]] = tyre_life[mask] ** 2

    y = df["lap_time_s"].to_numpy(dtype=float)

    coefs, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    residuals = y - X @ coefs
    residual_std = float(np.std(residuals, ddof=X.shape[1]))

    driver_offset = {reference_driver: 0.0}
    for d in other_drivers:
        driver_offset[d] = float(coefs[col_idx[f"driver:{d}"]])

    compound_offset = {reference_compound: 0.0}
    for c in other_compounds:
        compound_offset[c] = float(coefs[col_idx[f"compound:{c}"]])

    deg_linear = {c: float(coefs[col_idx[f"deg_lin:{c}"]]) for c in compounds}
    deg_quad = {c: float(coefs[col_idx[f"deg_quad:{c}"]]) for c in compounds}

    return PaceModel(
        intercept=float(coefs[col_idx["intercept"]]),
        reference_driver=reference_driver,
        reference_compound=reference_compound,
        driver_offset=driver_offset,
        compound_offset=compound_offset,
        fuel_effect_per_lap=float(coefs[col_idx["lap_number"]]),
        deg_linear=deg_linear,
        deg_quad=deg_quad,
        residual_std=residual_std,
        n_laps_fit=n,
        compounds=tuple(compounds),
    )
