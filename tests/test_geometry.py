"""
Tests for column-tile geometry in geometry.py.
"""

from geometry import bottom_column_tile_centers, top_column_tile_centers


# --- top column ---------------------------------------------------------


def test_top_column_first_tile_is_cap_flush_above_gap():
    """ Cap center is gap_top + tile_size/2 — its bottom edge sits AT gap_top. """
    centers = top_column_tile_centers(
        gap_top=400, tile_size=192, overlap=0, target_top=720,
    )
    assert centers[0] == 400 + 96   # 496


def test_top_column_tiles_stack_upward_without_overlap():
    """ With overlap=0 each tile's center is exactly tile_size above the previous.
    Stops once the previous tile's top edge reaches target_top. """
    centers = top_column_tile_centers(
        gap_top=400, tile_size=100, overlap=0, target_top=900,
    )
    # cap=450 (top=500), 550 (top=600), 650 (top=700), 750 (top=800), 850 (top=900). Stop.
    assert centers == [450, 550, 650, 750, 850]


def test_top_column_overlap_reduces_step():
    """ overlap > 0 means each successive tile is (tile_size - overlap) higher. """
    centers = top_column_tile_centers(
        gap_top=400, tile_size=100, overlap=10, target_top=900,
    )
    # First center = 450. Next = 450 + (100 - 10) = 540. Etc.
    assert centers[0] == 450
    diffs = [centers[i + 1] - centers[i] for i in range(len(centers) - 1)]
    for d in diffs:
        assert d == 90


def test_top_column_stops_after_passing_target_top():
    """ Stacking continues until the previous tile's top edge >= target_top. """
    centers = top_column_tile_centers(
        gap_top=0, tile_size=100, overlap=0, target_top=300,
    )
    # First center=50 (top edge=100). 100 < 300, keep going.
    # Second=150 (top=200). 200 < 300, keep.
    # Third=250 (top=300). 300 >= 300, stop after this one.
    # Wait — the condition is next_bottom < target_top, so after placing the third
    # tile, next_bottom = 300 which is not < 300, so loop exits without placing more.
    assert centers == [50, 150, 250]


# --- bottom column ------------------------------------------------------


def test_bottom_column_first_tile_is_cap_flush_below_gap():
    """ Cap center is gap_bottom - tile_size/2 — its top edge sits AT gap_bottom. """
    centers = bottom_column_tile_centers(
        gap_bottom=300, tile_size=192, overlap=0, target_bottom=0,
    )
    assert centers[0] == 300 - 96   # 204


def test_bottom_column_tiles_stack_downward_without_overlap():
    centers = bottom_column_tile_centers(
        gap_bottom=600, tile_size=100, overlap=0, target_bottom=0,
    )
    expected = [550, 450, 350, 250, 150, 50]
    assert centers == expected


def test_bottom_column_overlap_reduces_step():
    centers = bottom_column_tile_centers(
        gap_bottom=600, tile_size=100, overlap=10, target_bottom=0,
    )
    assert centers[0] == 550
    diffs = [centers[i] - centers[i + 1] for i in range(len(centers) - 1)]
    for d in diffs:
        assert d == 90


def test_bottom_column_stops_after_passing_target_bottom():
    """ Stops once previous tile's bottom edge <= target_bottom. """
    centers = bottom_column_tile_centers(
        gap_bottom=300, tile_size=100, overlap=0, target_bottom=0,
    )
    # Cap=250 (bottom=200). 200 > 0, continue.
    # Next=150 (bottom=100). 100 > 0, continue.
    # Next=50 (bottom=0). 0 not > 0, stop after this.
    assert centers == [250, 150, 50]


def test_bottom_column_extends_below_screen_with_negative_target():
    """ Oscillating bottom columns need to extend BELOW y=0 by amplitude. """
    centers = bottom_column_tile_centers(
        gap_bottom=200, tile_size=100, overlap=0, target_bottom=-100,
    )
    # cap=150, then 50, then -50. -50's bottom is -100 == target_bottom (not >).
    assert centers == [150, 50, -50]


# --- single-tile edge case ----------------------------------------------


def test_top_column_just_a_cap_when_gap_top_already_at_target():
    """ If gap_top is already at/past the target, only the cap is placed. """
    centers = top_column_tile_centers(
        gap_top=1000, tile_size=100, overlap=0, target_top=720,
    )
    # cap center = 1050, top edge = 1100. 1100 - 0 = 1100 >= 720, no more tiles.
    assert centers == [1050]
