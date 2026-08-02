import pytest

from app.auth import decrypt_mnemonic, encrypt_mnemonic, generate_mnemonic


def test_generate_mnemonic_is_24_words():
    mnemonic = generate_mnemonic()
    words = mnemonic.split()
    assert len(words) == 24


def test_generate_mnemonic_is_random():
    a = generate_mnemonic()
    b = generate_mnemonic()
    assert a != b


def test_round_trip():
    mnemonic = generate_mnemonic()
    encrypted, salt = encrypt_mnemonic(mnemonic, 'hunter2')
    assert encrypted != mnemonic
    assert len(salt) == 16

    decrypted = decrypt_mnemonic(encrypted, salt.hex(), 'hunter2')
    assert decrypted == mnemonic


def test_unique_salts_and_ciphertexts():
    mnemonic = generate_mnemonic()
    e1, s1 = encrypt_mnemonic(mnemonic, 'hunter2')
    e2, s2 = encrypt_mnemonic(mnemonic, 'hunter2')
    assert s1 != s2
    assert e1 != e2


def test_wrong_password_raises():
    mnemonic = generate_mnemonic()
    encrypted, salt = encrypt_mnemonic(mnemonic, 'hunter2')
    with pytest.raises(Exception):
        decrypt_mnemonic(encrypted, salt.hex(), 'wrongpass')


def test_tampered_ciphertext_raises():
    mnemonic = generate_mnemonic()
    encrypted, salt = encrypt_mnemonic(mnemonic, 'hunter2')
    flipped = ('1' if encrypted[0] == '0' else '0') + encrypted[1:]
    with pytest.raises(Exception):
        decrypt_mnemonic(flipped, salt.hex(), 'hunter2')
