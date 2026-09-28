from evaluation.lenient import lenient_match


def test_yes_no_synonyms_match_same_polarity_only():
    q = "X là chủ tịch đúng không?"
    assert lenient_match("Có", "Đúng", q, level="yn")
    assert lenient_match("Phải", "Có", q, level="yn")
    assert lenient_match("Sai", "Không", q, level="yn")
    assert not lenient_match("Có", "Không", q, level="yn")
    assert not lenient_match("Có", "Đúng", q, level="strict")


def test_format_synonyms():
    assert lenient_match("2006", "Năm 2006", "Khi nào?")
    assert lenient_match("8", "8 tuổi", "Ông ấy bao nhiêu tuổi?")
    assert lenient_match("34.4", "34,4", "Chênh bao nhiêu?")
    assert lenient_match("10400000", "10.400.000", "Lớn hơn bao nhiêu km²?")
    assert lenient_match("Burundi*", "Burundi", "Nước nào?")
    assert lenient_match("Thành phố New York", "New York", "Ở đâu?")
    assert lenient_match("Fabiano Caruana, Wesley So", "Fabiano Caruana và Wesley So", "Hai kỳ thủ nào?")
    assert lenient_match("Cao Lãnh, Sa Đéc", "Sa Đéc, Cao Lãnh", "Những đô thị nào?")


def test_format_level_keeps_real_differences():
    assert not lenient_match("1.713", "1.513", "Nhiều hơn bao nhiêu?")
    assert not lenient_match("8", "8 tuổi", "Bao nhiêu năm?")  # đơn vị gold khác đơn vị câu hỏi: không bỏ
    assert not lenient_match("8 năm", "8 tuổi", "Ông ấy bao nhiêu tuổi?")
    assert not lenient_match("Cao Lãnh, Sa Đéc", "Sa Đéc, Cao Lãnh", "Liệt kê theo thứ tự giảm dần?")
    assert not lenient_match("Hà Nội", "Null", "Ở đâu?")
    assert lenient_match("Null", "Null", "Ở đâu?")
