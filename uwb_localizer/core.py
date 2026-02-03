"""
Core localization module using multilateration algorithm.
"""
import math
from typing import Dict, Tuple, Optional
import localization as lx


def solve_position(d1: float, d2: float, d3: float, z_sign: int = +1, 
                   eps: float = 1e-9, L2: float = 0, L3: float = 0) -> Tuple[float, float, float]:
    """
    Trilateration using 3 anchors:
      A1=(0,0,0), A2=(L2,0,0), A3=(0,L3,0).
    Input: d1,d2,d3 — distances to A1,A2,A3 (in meters).
    Parameter z_sign: +1 — choose upper solution (z>=0), -1 — lower (z<=0).
    Returns (x,y,z).
    """
    if L2 <= 0 or L3 <= 0:
        raise ValueError("L2 and L3 must be positive")

    x = (L2*L2 + d1*d1 - d2*d2) / (2.0 * L2)
    y = (L3*L3 + d1*d1 - d3*d3) / (2.0 * L3)

    z2 = d1*d1 - x*x - y*y
    if z2 < 0:
        z2 = 0.0

    z = math.sqrt(z2) * (1 if z_sign >= 0 else -1)
    return x, y, z


def calibrated_linear(k, b, x):
    """Linear calibration: k * x + b"""
    return k * x + b


def calibrated_quadratic(a, b, c, x):
    """Quadratic calibration: a * x^2 + b * x + c"""
    return a * x**2 + b * x + c


def calibrated_cubic(a, b, c, d, x):
    """Cubic calibration: a * x^3 + b * x^2 + c * x + d"""
    return a * x**3 + b * x**2 + c * x + d


def multilateration(raw_data: Dict[int, float], 
                    anchor_positions: Dict[int, Tuple[float, float, float]], 
                    z_sign: int = 0) -> Tuple[float, float, float]:
    """
    Multilateration algorithm using localization library.
    
    :param raw_data: Dictionary mapping anchor IDs to distances (meters)
    :param anchor_positions: Dictionary mapping anchor IDs to (x, y, z) positions
    :param z_sign: z sign, used if there are two solutions (0 = auto, +1 = positive, -1 = negative)
    :return: (x, y, z) position tuple
    """
    P = lx.Project(mode='3D', solver='LSE')
    non_zero_data = {}
    
    for anchor_id in raw_data.keys():
        if raw_data[anchor_id] is not None:
            non_zero_data[anchor_id] = raw_data[anchor_id]

    if len(non_zero_data) < 3:
        raise ValueError(f"Not enough data for trilateration. Non-zero: {non_zero_data}, Input: {raw_data}")
    
    if len(anchor_positions) < 3:
        raise ValueError(f"Not enough anchor positions for trilateration: {anchor_positions}")

    matched_ids = list(set(non_zero_data.keys()) & set(anchor_positions.keys()))
    if len(matched_ids) < 3:
        raise ValueError(f"Not enough common anchors for trilateration. Matched: {matched_ids}")

    for anchor_id in matched_ids:
        P.add_anchor(anchor_id, anchor_positions[anchor_id])
    
    t, label = P.add_target()
    for anchor_id in matched_ids:
        t.add_measure(anchor_id, non_zero_data[anchor_id])
    
    P.solve()
    
    if z_sign != 0:
        t.loc.z = abs(t.loc.z) * z_sign
    
    return t.loc.x, t.loc.y, t.loc.z


class LocalizationEngine:
    """Main localization engine that processes distance measurements and calculates position."""
    
    def __init__(self, anchor_positions: Dict[int, Tuple[float, float, float]],
                 calibration_type: str = 'none',
                 calibration_params: list = None,
                 z_sign: int = 0,
                 min_range: float = 0.0,
                 max_range: float = 100.0):
        """
        Initialize localization engine.
        
        :param anchor_positions: Dictionary mapping anchor IDs to (x, y, z) positions
        :param calibration_type: Type of calibration ('none', 'linear', 'quadratic', 'cubic')
        :param calibration_params: Parameters for calibration function
        :param z_sign: z sign for position calculation
        :param min_range: Minimum valid range (meters)
        :param max_range: Maximum valid range (meters)
        """
        self.anchor_positions = anchor_positions
        self.calibration_type = calibration_type
        self.calibration_params = calibration_params or []
        self.z_sign = z_sign
        self.min_range = min_range
        self.max_range = max_range
        
        # Validate anchor positions
        if len(self.anchor_positions) < 3:
            raise ValueError("At least 3 anchor positions are required for trilateration")
    
    def calibrate(self, raw_distance: float) -> float:
        """Apply calibration to raw distance measurement."""
        if self.calibration_type == "linear":
            if len(self.calibration_params) != 2:
                raise ValueError("Linear calibration requires 2 parameters [k, b]")
            return calibrated_linear(self.calibration_params[0], self.calibration_params[1], raw_distance)
        elif self.calibration_type == "quadratic":
            if len(self.calibration_params) != 3:
                raise ValueError("Quadratic calibration requires 3 parameters [a, b, c]")
            return calibrated_quadratic(*self.calibration_params, raw_distance)
        elif self.calibration_type == "cubic":
            if len(self.calibration_params) != 4:
                raise ValueError("Cubic calibration requires 4 parameters [a, b, c, d]")
            return calibrated_cubic(*self.calibration_params, raw_distance)
        else:
            return raw_distance
    
    def validate_range(self, distance: float) -> bool:
        """Check if distance is within valid range."""
        return self.min_range <= distance <= self.max_range
    
    def calculate_position(self, distances: Dict[int, float]) -> Optional[Tuple[float, float, float]]:
        """
        Calculate position from distance measurements.
        
        :param distances: Dictionary mapping anchor IDs to calibrated distances (meters)
        :return: (x, y, z) position tuple or None if calculation fails
        """
        # Filter out None values and validate ranges
        valid_distances = {}
        for anchor_id, distance in distances.items():
            if distance is not None and self.validate_range(distance):
                valid_distances[anchor_id] = distance
        
        if len(valid_distances) < 3:
            return None
        
        try:
            return multilateration(valid_distances, self.anchor_positions, self.z_sign)
        except ValueError as e:
            print(f"Error in multilateration: {e}")
            return None
