"""The style/other classifier; its predecessor treated ``5`` inside ``50`` as the same answer."""

from scripts.analyze_repr_stage import classify


def test_a_number_that_is_a_substring_of_another_is_not_the_same_answer():
    assert classify("5", "5", "50") == "other"
    assert classify("140", "140", "1400 người") == "other"


def test_extra_words_around_the_same_answer_are_style():
    assert classify("Ninh Thuận", "Ninh Thuận", "tỉnh Ninh Thuận") == "extra_words"
    assert classify("2", "2", "thứ 2") == "extra_words"
    assert classify("Có", "Có", "Có, tất cả các tập đều đạt hạng 1") == "extra_words"


def test_a_gold_null_is_a_format_case_whatever_the_prediction_says():
    assert classify("Null", "null", "Không có thông tin cụ thể về cá nhân") == "null_format"


def test_case_and_trailing_period_do_not_count_as_a_difference_in_words():
    assert classify("Hà Nội", "Hà Nội", "hà nội.") == "extra_words"


def test_two_different_answers_are_other():
    assert classify("x-34", "x-34", "x-37") == "other"
    assert classify("Pich Votey Saravolay", "Pich Votey Saravolay", "Sun Sreymom") == "other"


def test_words_must_be_contiguous_and_in_order():
    assert classify("Thị xã Tân Châu", "Thị xã Tân Châu", "Tân Thị Châu xã") == "other"


def test_a_decimal_is_not_split_into_its_digits():
    assert classify("5", "5", "1.5") == "other"
    assert classify("5", "5", "1,5") == "other"
