def test_ci_red_probe() -> None:
    """Temporary probe: must make the backend CI job fail, then be removed."""
    assert False, "intentional CI red probe"
