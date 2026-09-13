from one_line_day_py.src.security import hash_password, verify_password


class TestSecurity:
    def test_hash_differs_from_plaintext(self):
        assert hash_password("hunter22") != "hunter22"

    def test_hashing_same_password_twice_differs(self):
        assert hash_password("hunter22") != hash_password("hunter22")

    def test_verify_password_succeeds_for_correct_password(self):
        hashed = hash_password("hunter22")
        assert verify_password("hunter22", hashed) is True

    def test_verify_password_fails_for_wrong_password(self):
        hashed = hash_password("hunter22")
        assert verify_password("wrong-password", hashed) is False
