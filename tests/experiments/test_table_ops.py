from experiments.table_representation.table_ops import table_op_answer


def _table(html: str, table_id: str = "demo") -> dict:
    return {"table_id": table_id, "table_title": "", "table_html": html}


def test_frequency_rank_returns_second_most_common_non_numeric_value():
    html = """
    <table>
      <tr><th>Số</th><th>VT</th><th>Cầu thủ</th></tr>
      <tr><td>1</td><td>HV</td><td>A</td></tr>
      <tr><td>3</td><td>HV</td><td>B</td></tr>
      <tr><td>4</td><td>HV</td><td>C</td></tr>
      <tr><td>6</td><td>HV</td><td>D</td></tr>
      <tr><td>8</td><td>TV</td><td>E</td></tr>
      <tr><td>9</td><td>TĐ</td><td>F</td></tr>
      <tr><td>10</td><td>TV</td><td>G</td></tr>
      <tr><td>12</td><td>HV</td><td>H</td></tr>
      <tr><td>14</td><td>TV</td><td>I</td></tr>
      <tr><td>15</td><td>HV</td><td>J</td></tr>
      <tr><td>16</td><td>TV</td><td>K</td></tr>
    </table>
    """
    question = "Ví trị nào được sử dụng nhiều thứ 2 trong bảng dữ liệu này?"
    result = table_op_answer(_table(html), question)
    assert result is not None
    assert result.value == "TV"
    assert result.op == "frequency_rank"


def test_frequency_rank_does_not_fire_on_yes_no_or_rank_lookup():
    html = """
    <table>
      <tr><th>Tập</th><th>Hạng</th></tr>
      <tr><td>Pilot</td><td>1</td></tr>
      <tr><td>Hai</td><td>2</td></tr>
    </table>
    """
    table = _table(html)
    assert table_op_answer(table, "Có tập phim nào xếp hạng #2 không?") is None
    assert table_op_answer(table, "Tập phim nào xếp hạng nhất trong khung giờ?") is None


def test_filtered_min_returns_name_from_matching_rows():
    html = """
    <table>
      <tr><th>Tên</th><th>Giá trị tài sản</th><th>Quốc gia</th></tr>
      <tr><td>Prince</td><td>20.3</td><td>Ả Rập Xê Út Liban</td></tr>
      <tr><td>Maan Al-Sanea</td><td>7.5</td><td>Ả Rập Xê Út</td></tr>
      <tr><td>Sulaiman Al Rajhi</td><td>7.4</td><td>Ả Rập Xê Út</td></tr>
    </table>
    """
    result = table_op_answer(
        _table(html),
        "Người nào có giá trị tài sản thấp nhất và đến từ Ả Rập Xê Út?",
    )
    assert result is not None
    assert result.value == "Sulaiman Al Rajhi"
    assert result.op == "filtered_extremum"


def test_filtered_min_floors_uses_city_cell_in_question():
    html = """
    <table>
      <tr><th>Tòa nhà</th><th>Thành phố</th><th>Tầng</th></tr>
      <tr><td>Al Noor Tower</td><td>Casablanca</td><td>114</td></tr>
      <tr><td>JW Marriott Hotel</td><td>Casablanca</td><td>42</td></tr>
      <tr><td>Atlantic Tower</td><td>Casablanca</td><td>37</td></tr>
      <tr><td>Hazina Trade Centre</td><td>Nairobi</td><td>39</td></tr>
    </table>
    """
    result = table_op_answer(
        _table(html),
        "Tòa nhà nào thuộc Casablanca và có ít tầng nhất?",
    )
    assert result is not None
    assert result.value == "Atlantic Tower"


def test_list_rows_keeps_matching_entity_and_result():
    html = """
    <table>
      <tr><th>Hạng mục</th><th>Người được đề cử</th><th>Kết quả</th></tr>
      <tr><td>Chương trình đa dạng hay nhất</td><td>Running Man</td><td>Đoạt giải</td></tr>
      <tr><td>Cặp đôi hoàn hảo</td><td>Gary &amp; Song Ji-hyo</td><td>Đoạt giải</td></tr>
      <tr><td>Giải thưởng Tinh thần Giải trí</td><td>Running Man</td><td>Đoạt giải</td></tr>
      <tr><td>Chương trình cuối tuần</td><td>Running Man</td><td>Đề cử</td></tr>
    </table>
    """
    result = table_op_answer(
        _table(html),
        "Liệt kê các hạng mục mà Running Man đoạt giải?",
    )
    assert result is not None
    assert result.op == "list_rows"
    assert result.value == "Chương trình đa dạng hay nhất, Giải thưởng Tinh thần Giải trí"


def test_list_rows_filters_year_in_date_cells():
    html = """
    <table>
      <tr><th>Ca sĩ tham gia</th><th>Ngày phát hành</th></tr>
      <tr><td>Văn Mai Hương</td><td>11/07/2022</td></tr>
      <tr><td>Lương Bích Hữu</td><td>13/03/2023</td></tr>
      <tr><td>Khải Đăng</td><td>07/04/2023</td></tr>
      <tr><td>Doãn Hiếu</td><td>04/07/2023</td></tr>
    </table>
    """
    result = table_op_answer(
        _table(html),
        "Liệt kê tên các ca sĩ có ngày phát hành vào năm 2023?",
    )
    assert result is not None
    assert result.value == "Lương Bích Hữu, Khải Đăng, Doãn Hiếu"


def test_climate_argmax_returns_month_header():
    html = """
    <table>
      <tr><th>Tháng</th><th>1</th><th>2</th><th>7</th><th>12</th><th>Năm</th></tr>
      <tr><td>% Độ ẩm</td><td>63</td><td>65</td><td>86</td><td>65</td><td>74.5</td></tr>
      <tr><td>Giáng thủy mm</td><td>138</td><td>172</td><td>196</td><td>140</td><td>2000</td></tr>
    </table>
    """
    result = table_op_answer(_table(html), "Khi nào thì có % Độ ẩm cao nhất?")
    assert result is not None
    assert result.value == "7"
    assert result.op == "climate_extremum"


def test_why_and_count_questions_do_not_use_table_ops():
    html = """
    <table>
      <tr><th>Tên</th><th>Kg</th></tr>
      <tr><td>Nhi</td><td>50</td></tr>
      <tr><td>Ngân</td><td>60</td></tr>
    </table>
    """
    table = _table(html)
    assert table_op_answer(table, "Tại sao Nhi không phải là người có cân nặng lớn nhất đội?") is None
    assert table_op_answer(table, "Có bao nhiêu người trong bảng?") is None
