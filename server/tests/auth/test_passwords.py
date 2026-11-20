from games_server.auth.passwords import hash_password, is_password_hash, verify_password


def test_hash_verifies_only_the_original_password() -> None:
    password_hash = hash_password("hunter2")

    assert verify_password(password_hash, "hunter2")
    assert not verify_password(password_hash, "hunter3")
    assert not verify_password(password_hash, "")


def test_hash_does_not_contain_the_password() -> None:
    assert "hunter2" not in hash_password("hunter2")


def test_hashes_are_salted() -> None:
    assert hash_password("hunter2") != hash_password("hunter2")


def test_recognizes_argon2_hashes() -> None:
    assert is_password_hash(hash_password("hunter2"))
    assert not is_password_hash("hunter2")
    assert not is_password_hash("")
