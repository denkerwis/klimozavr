from klimozawr.core.net import is_valid_target


def test_valid_targets_accept_ipv4_and_domains() -> None:
    assert is_valid_target("192.168.0.1")
    assert is_valid_target("ya.ru")
    assert is_valid_target("host-1.example.local")


def test_invalid_targets_reject_bad_values() -> None:
    assert not is_valid_target("")
    assert not is_valid_target("999.999.1.1")
    assert not is_valid_target("-bad.example.com")
    assert not is_valid_target("bad..example.com")
