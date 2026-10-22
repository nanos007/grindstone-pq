import numpy as np

from ref import sha2, wots_c
from runner import configs, instances


def test_wots_records_match_reference_template():
    mat = instances.wots_materials("t", "cfg", 5, 8)
    recs = instances.wots_records(mat)
    for i in range(8):
        seed, adrs, m = (bytes(mat[k][i]) for k in ("seed", "adrs", "m"))
        words, off = wots_c.final_block_template(adrs, m, instances.LAYOUT)
        assert off == instances.CTR_OFF
        assert list(recs[i, :8]) == list(sha2.seed_midstate(seed))
        assert list(recs[i, 8:]) == words


def test_stream_is_deterministic_and_index_addressed():
    a = instances.stream("run", "cfg", 0, 10, 54)
    b = instances.stream("run", "cfg", 4, 3, 54)
    assert np.array_equal(a[4:7], b)
    assert not np.array_equal(a, instances.stream("run2", "cfg", 0, 10, 54))


def test_shortlist_configs_cover_every_point():
    cfgs = configs.from_shortlist()
    served = {pid for c in cfgs for pid in c.param_ids}
    assert len(served) == 40
    by_id = {c.id: c for c in cfgs}
    # z = 1 at w = 256 reproduces the shortlist's analytic expectation
    assert by_id["wots-w256-S1912-z1"].expected_tries() == np.float64(185527.6080236517)
