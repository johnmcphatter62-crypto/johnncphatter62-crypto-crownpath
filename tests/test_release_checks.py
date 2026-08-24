from crownpath.release_checks import release_checks

def test_release_checks_returns_guarded_result():
    result=release_checks()
    assert "checks" in result
    assert "release_ready" in result
