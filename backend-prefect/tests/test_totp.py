import pytest
from app.totp import hotp, totp, match_window

SECRET = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"

@pytest.mark.parametrize("timestamp,expected", [(59,"94287082"),(1111111109,"07081804"),
    (1111111111,"14050471"),(1234567890,"89005924"),(2000000000,"69279037"),(20000000000,"65353130")])
def test_rfc6238_sha1(timestamp, expected):
    assert totp(SECRET, timestamp, 8) == expected

@pytest.mark.parametrize("counter,expected", list(enumerate(["755224","287082","359152","969429","338314","254676","287922","162583","399871","520489"])))
def test_rfc4226(counter, expected):
    assert hotp(SECRET, counter) == expected

@pytest.mark.parametrize("delta", [-1,0,1])
def test_windows(delta):
    assert match_window(SECRET,totp(SECRET,1234567890+delta*30),1234567890) == delta

def test_reject_outside_window_and_non_numeric():
    assert match_window(SECRET,totp(SECRET,1234567890+60),1234567890) is None
    assert match_window(SECRET,"１２３４５６",1234567890) is None
