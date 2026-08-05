from src.agents.answer_normalization import _list_variants


def test_list_variants_preserve_source_order_and_do_not_expand_candidates():
    answer = (
        "Eee 900/901, Eee 1000, Eee 1005HR, "
        "Eee Pad Transformer/Transformer Pad 300 Series"
    )

    assert _list_variants(answer) == [answer]
