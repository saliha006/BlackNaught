import random
import sys
import uuid

import pytest

from app import crypto
from app.ingest import feeds, store
from app.seed import DEVICES, fake_contact, keys, patient_row, seed
from app.seed import main as seed_main

# NIST/McGrew-Viega GCM spec, AES-256 test cases 13, 14 and 16
KAT = [
    ("00" * 32, "00" * 12, "", "", "", "530f8afbc74536b9a963b4f1c4cb738b"),
    ("00" * 32, "00" * 12, "00" * 16, "", "cea7403d4d606b6e074ec5d3baf39d18", "d0d1c8a799996bf0265b98b5d48ab919"),
    ("feffe9928665731c6d6a8f9467308308feffe9928665731c6d6a8f9467308308",
     "cafebabefacedbaddecaf888",
     "d9313225f88406e5a55909c5aff5269a86a7a9531534f7da2e4c303d8a318a721c3c0c95956809532fcf0e2449a6b525b16aedf5aa0de657ba637b39",
     "feedfacedeadbeeffeedfacedeadbeefabaddad2",
     "522dc1f099567d07f47f37a32a84427d643a8cdcbfe5c0c97598a2bd2555d1aa8cb08e48590dbb3da7b08b1056828838c5f61e6393ba7a0abcc9f662",
     "76fc6ece0f4e1768cddf8853bb2d551b"),
]


@pytest.mark.parametrize("key,iv,pt,aad,ct,tag", KAT)
def test_gcm_known_answers(key, iv, pt, aad, ct, tag):
    got_ct, got_tag = crypto.seal(bytes.fromhex(key), bytes.fromhex(iv), bytes.fromhex(pt), bytes.fromhex(aad))
    assert (got_ct.hex(), got_tag.hex()) == (ct, tag)
    assert crypto.open_sealed(bytes.fromhex(key), bytes.fromhex(iv), got_ct, got_tag, bytes.fromhex(aad)) == \
        bytes.fromhex(pt)


def test_roundtrip_and_tamper_detection():
    key = bytes(range(32))
    blob = crypto.encrypt(key, b"+44 7700 900123", b"patient-1")
    assert crypto.decrypt(key, blob, b"patient-1") == b"+44 7700 900123"
    assert crypto.encrypt(key, b"x", b"a") != crypto.encrypt(key, b"x", b"a")  # fresh nonce every time
    flipped = blob[:15] + bytes([blob[15] ^ 1]) + blob[16:]
    for bad_blob, aad, k in [(flipped, b"patient-1", key), (blob, b"patient-2", key),
                             (blob, b"patient-1", bytes(32)), (blob[:-1] + b"\x00", b"patient-1", key)]:
        with pytest.raises(crypto.InvalidTag):
            crypto.decrypt(k, bad_blob, aad)
    with pytest.raises(crypto.InvalidTag):
        crypto.decrypt(key, b"short", b"")


def test_key_length_enforced():
    with pytest.raises(ValueError, match="32-byte"):
        crypto.encrypt(b"short", b"x", b"")


def test_blind_index_is_keyed_and_deterministic():
    a, b = bytes(32), bytes([1]) * 32
    assert crypto.blind_index(a, "N1 3LD") == crypto.blind_index(a, "N1 3LD") != crypto.blind_index(b, "N1 3LD")
    assert len(crypto.blind_index(a, "N1 3LD")) == 32


def test_fake_contacts_are_ofcom_drama_numbers():
    rng = random.Random(1)
    assert all(fake_contact(rng).startswith("+44 7700 900") for _ in range(200))


def test_patient_row_respects_device_ranges():
    rng = random.Random(3)
    dek, bidx = bytes(32), bytes(32)
    spans = {d: span for d, _, span, _ in DEVICES}
    for _ in range(300):
        row = patient_row(rng, "N1 3LD", 51.54, -0.09, dek, bidx)
        lo, hi = spans[row["device"]]
        assert lo <= row["reserve"] <= hi and 1 <= row["severity"] <= 5
    pinned = patient_row(rng, "N1 3LD", 51.54, -0.09, dek, bidx, "ventilator", 15.0, False)
    assert (pinned["device"], pinned["reserve"], pinned["backup"]) == ("ventilator", 15.0, False)


@pytest.mark.anyio
async def test_seed_places_patients_on_real_footprints(db_factory, superuser):
    superuser.run("TRUNCATE outage, outage_version, postcode_geo, patient RESTART IDENTITY CASCADE")
    superuser.run("INSERT INTO postcode_geo VALUES ('N1 3LD', 51.5456, -0.0890, 'E01', 'Islington', true, now()),"
                  " ('N1 3LE', 51.5445, -0.0891, 'E01', 'Islington', true, now())")
    o = feeds.Outage("ukpn", "INCD-9", "active", feeds.timeparse.iso("2026-10-17T20:00:00Z"),
                     postcodes=["N1 3LD", "N1 3LE"], lat=51.545, lon=-0.089)
    await store.sync(db_factory("bn_ingest"), "ukpn", [o], feeds.timeparse.iso("2026-10-17T21:00:00Z"))
    n = seed(superuser, per_outage=15, two_houses=1, rng=random.Random(5))
    assert n == 17
    assert superuser.run("SELECT count(DISTINCT cell_l1) FROM patient")[0][0] >= 1
    dek, bidx = keys()
    contact_ct, pid = superuser.run("SELECT contact_ct, patient_id FROM patient LIMIT 1")[0]
    assert crypto.decrypt(dek, bytes(contact_ct), uuid.UUID(str(pid)).bytes).startswith(b"+44 7700 900")
    match = superuser.run("SELECT count(*) FROM patient WHERE postcode_bidx = :b",
                          b=crypto.blind_index(bidx, "N1 3LD"))[0][0]
    assert match >= 2  # both demo houses sit on N1 3LD
    assert superuser.run("SELECT count(*) FROM patient WHERE device = 'ventilator' AND reserve_h = 15")[0][0] >= 1


def test_seed_cli(superuser, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["seed", "--per-outage", "1", "--database", "blacknaught_test"])
    seed_main()
    assert capsys.readouterr().out.startswith("patients:")
