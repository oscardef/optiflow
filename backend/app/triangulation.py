"""
Triangulation service for calculating tag positions from UWB distance measurements
"""
import math
from typing import List, Tuple, Optional
from datetime import datetime

class TriangulationService:
    """
    Calculates 2D position of a tag based on distance measurements from multiple anchors
    Uses trilateration algorithm (geometric intersection of circles)
    """
    
    @staticmethod
    def calculate_position(
        measurements: List[Tuple[float, float, float]]
    ) -> Optional[Tuple[float, float, float]]:
        """
        Calculate tag position using trilateration
        
        Args:
            measurements: List of (anchor_x, anchor_y, distance) tuples
            
        Returns:
            Tuple of (x, y, confidence) or None if calculation fails
            
        Algorithm:
        - With 2 anchors: Returns midpoint (low confidence)
        - With 3+ anchors: Uses least-squares trilateration
        """
        if len(measurements) < 2:
            return None
        
        if len(measurements) == 2:
            # With 2 anchors, we can only estimate the midpoint
            return TriangulationService._two_anchor_position(measurements)
        
        # With 3+ anchors, use proper trilateration
        return TriangulationService._multilateration(measurements)
    
    @staticmethod
    def _two_anchor_position(
        measurements: List[Tuple[float, float, float]]
    ) -> Tuple[float, float, float]:
        """
        Calculate approximate position with only 2 anchors
        Returns the midpoint between the two circles (low confidence)
        """
        (x1, y1, r1), (x2, y2, r2) = measurements[0], measurements[1]
        
        # Distance between anchors
        d = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        
        # If circles don't intersect meaningfully, return weighted midpoint
        if d > (r1 + r2) or d < abs(r1 - r2):
            # Weighted average based on distances
            total = r1 + r2
            x = (x1 * r2 + x2 * r1) / total
            y = (y1 * r2 + y2 * r1) / total
            return (x, y, 0.3)  # Low confidence
        
        # Calculate intersection point
        a = (r1**2 - r2**2 + d**2) / (2 * d)
        h = math.sqrt(max(0, r1**2 - a**2))
        
        # Point on line between circles
        x_mid = x1 + a * (x2 - x1) / d
        y_mid = y1 + a * (y2 - y1) / d
        
        # We'll take the average of both intersection points
        # (In reality, we'd need a 3rd anchor to disambiguate)
        x = x_mid
        y = y_mid
        
        return (x, y, 0.5)  # Medium confidence
    
    @staticmethod
    def _multilateration(
        measurements: List[Tuple[float, float, float]]
    ) -> Tuple[float, float, float]:
        """
        Calculate position using 3+ anchors with least-squares method
        More accurate and provides better confidence scores
        """
        n = len(measurements)
        
        # Set up matrices for least squares: Ax = b
        # We'll solve for (x, y) position
        A = []
        b = []
        
        # Use first anchor as reference point
        x1, y1, r1 = measurements[0]
        
        for i in range(1, n):
            xi, yi, ri = measurements[i]
            
            # Linear equation derived from:
            # (x - x1)^2 + (y - y1)^2 - r1^2 = (x - xi)^2 + (y - yi)^2 - ri^2
            A.append([2 * (xi - x1), 2 * (yi - y1)])
            b.append(
                xi**2 - x1**2 + yi**2 - y1**2 - ri**2 + r1**2
            )
        
        # Solve using least squares
        try:
            x, y = TriangulationService._least_squares(A, b)
            
            # Calculate confidence based on residual error
            confidence = TriangulationService._calculate_confidence(x, y, measurements)
            
            return (x, y, confidence)
        
        except Exception as e:
            print(f"Trilateration failed: {e}")
            # Fallback to centroid
            x = sum(m[0] for m in measurements) / n
            y = sum(m[1] for m in measurements) / n
            return (x, y, 0.2)  # Very low confidence
    
    @staticmethod
    def _least_squares(A: List[List[float]], b: List[float]) -> Tuple[float, float]:
        """
        Solve Ax = b using least squares method
        For 2D position: x = [x_pos, y_pos]
        """
        # Convert to numpy-like calculations without numpy
        # For 2x2 case, we can solve directly
        
        # A^T * A
        n = len(A)
        m = len(A[0])  # Should be 2
        
        ATA = [[0.0] * m for _ in range(m)]
        for i in range(m):
            for j in range(m):
                for k in range(n):
                    ATA[i][j] += A[k][i] * A[k][j]
        
        # A^T * b
        ATb = [0.0] * m
        for i in range(m):
            for k in range(n):
                ATb[i] += A[k][i] * b[k]
        
        # Solve 2x2 system: ATA * x = ATb
        det = ATA[0][0] * ATA[1][1] - ATA[0][1] * ATA[1][0]
        
        if abs(det) < 1e-10:
            raise ValueError("Singular matrix")
        
        x = (ATA[1][1] * ATb[0] - ATA[0][1] * ATb[1]) / det
        y = (ATA[0][0] * ATb[1] - ATA[1][0] * ATb[0]) / det
        
        return (x, y)
    
    @staticmethod
    def _calculate_confidence(
        x: float, 
        y: float, 
        measurements: List[Tuple[float, float, float]]
    ) -> float:
        """
        Calculate confidence score (0-1) based on how well the position
        fits all the distance measurements
        """
        errors = []
        
        for anchor_x, anchor_y, distance in measurements:
            calculated_dist = math.sqrt((x - anchor_x)**2 + (y - anchor_y)**2)
            error = abs(calculated_dist - distance)
            errors.append(error)
        
        # Average error in cm
        avg_error = sum(errors) / len(errors)
        
        # Convert to confidence (exponential decay)
        # Error of 0cm = 1.0 confidence
        # Error of 50cm = ~0.37 confidence
        # Error of 100cm = ~0.14 confidence
        confidence = math.exp(-avg_error / 50.0)
        
        return min(1.0, max(0.0, confidence))
