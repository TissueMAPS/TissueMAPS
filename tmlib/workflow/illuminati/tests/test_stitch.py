from tmlib.workflow.illuminati import stitch


def test_guess_stitch_dimensions_1_vertical():
    assert stitch.guess_stitch_dimensions(1, 'vertical') == (1, 1)


def test_guess_stitch_dimensions_1_horizontal():
    assert stitch.guess_stitch_dimensions(1, 'horizontal') == (1, 1)


def test_guess_stitch_dimensions_2_vertical():
    assert stitch.guess_stitch_dimensions(2, 'vertical') == (2, 1)


def test_guess_stitch_dimensions_2_horizontal():
    assert stitch.guess_stitch_dimensions(2, 'horizontal') == (1, 2)


def test_guess_stitch_dimensions_3_vertical():
    assert stitch.guess_stitch_dimensions(3, 'vertical') == (3, 1)


def test_guess_stitch_dimensions_3_horizontal():
    assert stitch.guess_stitch_dimensions(3, 'horizontal') == (1, 3)


def test_guess_stitch_dimensions_4_vertical():
    assert stitch.guess_stitch_dimensions(4, 'vertical') == (2, 2)


def test_guess_stitch_dimensions_4_horizontal():
    assert stitch.guess_stitch_dimensions(4, 'horizontal') == (2, 2)


def test_guess_stitch_dimensions_5_vertical():
    assert stitch.guess_stitch_dimensions(5, 'vertical') == (3, 2)


def test_guess_stitch_dimensions_5_horizontal():
    assert stitch.guess_stitch_dimensions(5, 'horizontal') == (2, 3)


def test_guess_stitch_dimensions_6_vertical():
    assert stitch.guess_stitch_dimensions(6, 'vertical') == (3, 2)


def test_guess_stitch_dimensions_6_horizontal():
    assert stitch.guess_stitch_dimensions(6, 'horizontal') == (2, 3)


def test_guess_stitch_dimensions_7_vertical():
    assert stitch.guess_stitch_dimensions(7, 'vertical') == (4, 2)


def test_guess_stitch_dimensions_7_horizontal():
    assert stitch.guess_stitch_dimensions(7, 'horizontal') == (2, 4)


def test_guess_stitch_dimensions_8_vertical():
    assert stitch.guess_stitch_dimensions(8, 'vertical') == (4, 2)


def test_guess_stitch_dimensions_8_horizontal():
    assert stitch.guess_stitch_dimensions(8, 'horizontal') == (2, 4)


def test_guess_stitch_dimensions_9_vertical():
    assert stitch.guess_stitch_dimensions(9, 'vertical') == (3, 3)


def test_guess_stitch_dimensions_9_horizontal():
    assert stitch.guess_stitch_dimensions(9, 'horizontal') == (3, 3)


def test_guess_stitch_dimensions_10_vertical():
    assert stitch.guess_stitch_dimensions(10, 'vertical') == (5, 2)


def test_guess_stitch_dimensions_10_horizontal():
    assert stitch.guess_stitch_dimensions(10, 'horizontal') == (2, 5)


def test_guess_stitch_dimensions_22_vertical():
    assert stitch.guess_stitch_dimensions(22, 'vertical') == (8, 3)


def test_guess_stitch_dimensions_22_horizontal():
    assert stitch.guess_stitch_dimensions(22, 'horizontal') == (3, 8)


def test_guess_stitch_dimensions_73_vertical():
    assert stitch.guess_stitch_dimensions(73, 'vertical') == (15, 5)


def test_guess_stitch_dimensions_73_horizontal():
    assert stitch.guess_stitch_dimensions(73, 'horizontal') == (5, 15)
