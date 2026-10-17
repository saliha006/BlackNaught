"""AES-256-GCM through the image's libcrypto, and an HMAC blind index for postcode matching.

The `cryptography` package has no s390x wheel and isn't in IBM's image, and `openssl enc` can't do GCM.
Calling OpenSSL's EVP API through ctypes keeps the CPACF claim true: on s390x OpenSSL routes AES-GCM to the
KMA instruction. Format: nonce(12) ‖ ciphertext ‖ tag(16); the AAD binds a ciphertext to its row.
"""
import ctypes
import ctypes.util
import hashlib
import hmac
import os

NONCE_LEN = 12
TAG_LEN = 16
KEY_LEN = 32
_EVP_CTRL_GCM_SET_IVLEN = 0x9
_EVP_CTRL_GCM_GET_TAG = 0x10
_EVP_CTRL_GCM_SET_TAG = 0x11


class InvalidTag(ValueError):
    pass


def _load() -> ctypes.CDLL:
    lib = ctypes.CDLL(ctypes.util.find_library("crypto") or "libcrypto.so.3")
    vp, ip, i = ctypes.c_void_p, ctypes.POINTER(ctypes.c_int), ctypes.c_int
    signatures = {
        "EVP_CIPHER_CTX_new": ([], vp),
        "EVP_CIPHER_CTX_free": ([vp], None),
        "EVP_aes_256_gcm": ([], vp),
        "EVP_EncryptInit_ex": ([vp, vp, vp, ctypes.c_char_p, ctypes.c_char_p], i),
        "EVP_DecryptInit_ex": ([vp, vp, vp, ctypes.c_char_p, ctypes.c_char_p], i),
        # output buffers are raw addresses so the Final call can write at an offset into the same buffer
        "EVP_EncryptUpdate": ([vp, vp, ip, ctypes.c_char_p, i], i),
        "EVP_DecryptUpdate": ([vp, vp, ip, ctypes.c_char_p, i], i),
        "EVP_EncryptFinal_ex": ([vp, vp, ip], i),
        "EVP_DecryptFinal_ex": ([vp, vp, ip], i),
        "EVP_CIPHER_CTX_ctrl": ([vp, i, i, vp], i),
    }
    for name, (args, res) in signatures.items():
        fn = getattr(lib, name)
        fn.argtypes, fn.restype = args, res
    return lib


_lib = _load()


def _check(ok: int, step: str) -> None:
    if ok != 1:
        raise RuntimeError(f"libcrypto {step} failed")


def _at(buffer: ctypes.Array, offset: int = 0) -> int:
    return ctypes.addressof(buffer) + offset


def _key(key: bytes) -> bytes:
    if len(key) != KEY_LEN:
        raise ValueError("AES-256 needs a 32-byte key")
    return key


def seal(key: bytes, nonce: bytes, plaintext: bytes, aad: bytes) -> tuple[bytes, bytes]:
    """Raw GCM encrypt with a caller-supplied nonce (exposed for known-answer tests)."""
    ctx = _lib.EVP_CIPHER_CTX_new()
    try:
        _check(_lib.EVP_EncryptInit_ex(ctx, _lib.EVP_aes_256_gcm(), None, None, None), "init")
        _check(_lib.EVP_CIPHER_CTX_ctrl(ctx, _EVP_CTRL_GCM_SET_IVLEN, len(nonce), None), "ivlen")
        _check(_lib.EVP_EncryptInit_ex(ctx, None, None, _key(key), nonce), "key")
        n = ctypes.c_int(0)
        if aad:
            _check(_lib.EVP_EncryptUpdate(ctx, None, ctypes.byref(n), aad, len(aad)), "aad")
        out = ctypes.create_string_buffer(len(plaintext) + 16)
        _check(_lib.EVP_EncryptUpdate(ctx, _at(out), ctypes.byref(n), plaintext, len(plaintext)), "update")
        written = n.value
        _check(_lib.EVP_EncryptFinal_ex(ctx, _at(out, written), ctypes.byref(n)), "final")
        tag = ctypes.create_string_buffer(TAG_LEN)
        _check(_lib.EVP_CIPHER_CTX_ctrl(ctx, _EVP_CTRL_GCM_GET_TAG, TAG_LEN, _at(tag)), "tag")
        return out.raw[:written + n.value], tag.raw
    finally:
        _lib.EVP_CIPHER_CTX_free(ctx)


def open_sealed(key: bytes, nonce: bytes, ciphertext: bytes, tag: bytes, aad: bytes) -> bytes:
    ctx = _lib.EVP_CIPHER_CTX_new()
    try:
        _check(_lib.EVP_DecryptInit_ex(ctx, _lib.EVP_aes_256_gcm(), None, None, None), "init")
        _check(_lib.EVP_CIPHER_CTX_ctrl(ctx, _EVP_CTRL_GCM_SET_IVLEN, len(nonce), None), "ivlen")
        _check(_lib.EVP_DecryptInit_ex(ctx, None, None, _key(key), nonce), "key")
        n = ctypes.c_int(0)
        if aad:
            _check(_lib.EVP_DecryptUpdate(ctx, None, ctypes.byref(n), aad, len(aad)), "aad")
        out = ctypes.create_string_buffer(len(ciphertext) + 16)
        _check(_lib.EVP_DecryptUpdate(ctx, _at(out), ctypes.byref(n), ciphertext, len(ciphertext)), "update")
        written = n.value
        tag_buf = ctypes.create_string_buffer(tag, TAG_LEN)
        _check(_lib.EVP_CIPHER_CTX_ctrl(ctx, _EVP_CTRL_GCM_SET_TAG, TAG_LEN, _at(tag_buf)), "settag")
        if _lib.EVP_DecryptFinal_ex(ctx, _at(out, written), ctypes.byref(n)) != 1:
            raise InvalidTag("authentication failed: ciphertext, tag or AAD was altered")
        return out.raw[:written + n.value]
    finally:
        _lib.EVP_CIPHER_CTX_free(ctx)


def encrypt(key: bytes, plaintext: bytes, aad: bytes) -> bytes:
    # random 96-bit nonces: our volume is far below the 2^32-messages-per-key limit for random GCM nonces
    nonce = os.urandom(NONCE_LEN)
    ciphertext, tag = seal(key, nonce, plaintext, aad)
    return nonce + ciphertext + tag


def decrypt(key: bytes, blob: bytes, aad: bytes) -> bytes:
    if len(blob) < NONCE_LEN + TAG_LEN:
        raise InvalidTag("blob too short")
    return open_sealed(key, blob[:NONCE_LEN], blob[NONCE_LEN:-TAG_LEN], blob[-TAG_LEN:], aad)


def blind_index(key: bytes, normalised_postcode: str) -> bytes:
    """Equality match on postcodes without storing them; leaks only that two rows share a postcode."""
    return hmac.new(key, normalised_postcode.encode(), hashlib.sha256).digest()
