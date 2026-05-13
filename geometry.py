"""
Pure-Python geometry helpers used by the obstacle spawners.

The column-spawning code in main.py needs to compute a list of (cap + mid)
tile center-y positions that stack up from the gap edge to past the screen
edge, with a per-tile overlap to hide art seams. That math is independent
of arcade sprites and can be tested in isolation.
"""

from __future__ import annotations


def top_column_tile_centers(
    gap_top: float,
    tile_size: float,
    overlap: float,
    target_top: float,
) -> list[float]:
    """ Center-y positions for the tiles that make up the TOP column
    (hanging from the ceiling). Index 0 is the cap (flush above the gap),
    later indices stack upward toward the ceiling.

    Each tile is ``tile_size`` tall and the bottom edge of tile ``n+1``
    overlaps the top edge of tile ``n`` by ``overlap`` pixels so the
    visible-art seams disappear.

    Stacking stops as soon as the previous tile's top edge has reached
    ``target_top`` (typically WINDOW_HEIGHT + a margin for oscillating gaps).
    """
    centers: list[float] = []
    # Cap: bottom edge flush against gap_top
    cap_center = gap_top + tile_size / 2
    centers.append(cap_center)

    # next_bottom = previous tile top edge - overlap
    next_bottom = cap_center + tile_size / 2 - overlap
    while next_bottom < target_top:
        center = next_bottom + tile_size / 2
        centers.append(center)
        next_bottom = center + tile_size / 2 - overlap
    return centers


def bottom_column_tile_centers(
    gap_bottom: float,
    tile_size: float,
    overlap: float,
    target_bottom: float,
) -> list[float]:
    """ Center-y positions for the tiles that make up the BOTTOM column
    (rising from the floor). Index 0 is the cap (flush below the gap),
    later indices stack downward toward the floor.

    Stops once the previous tile's bottom edge has reached
    ``target_bottom`` (typically 0, or below for oscillating gaps).
    """
    centers: list[float] = []
    cap_center = gap_bottom - tile_size / 2
    centers.append(cap_center)

    next_top = cap_center - tile_size / 2 + overlap
    while next_top > target_bottom:
        center = next_top - tile_size / 2
        centers.append(center)
        next_top = center - tile_size / 2 + overlap
    return centers
