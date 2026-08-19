r"""The path a share is shown with, against the path the server has.

srvsvc answers with a Windows path because the protocol has no other kind: a
Samba share on ``/tank/projects`` is reported as ``C:\tank\projects``. Shown
unchanged, the console contradicts the server's own ``net conf list`` about the
one field that decides which directory the share publishes — and it is a field
an administrator might reasonably retype.
"""

from __future__ import annotations

import pytest

from samfscon.srv.shares import _normalise_path


@pytest.mark.parametrize(
    ("reported", "shown"),
    [
        # What Samba actually sends for a Unix share.
        (r"C:\tank\samfscon-test", "/tank/samfscon-test"),
        (r"C:\srv\shares\projects", "/srv/shares/projects"),
        # Separators already converted, drive letter still there.
        ("C:/tank/share", "/tank/share"),
        # Not always C:. Whatever the letter, it is fabricated.
        (r"D:\data", "/data"),
        (r"z:\data", "/data"),
        # A server that reports the honest path changes nothing.
        ("/srv/shares/projects", "/srv/shares/projects"),
        # Nothing to show is nothing to show.
        ("", None),
        (None, None),
    ],
)
def test_the_path_is_shown_the_way_the_server_stores_it(
    reported: str | None, shown: str | None
) -> None:
    assert _normalise_path(reported) == shown


@pytest.mark.parametrize("path", ["C:", "C", "/c:/tank", "share:/tank"])
def test_only_a_leading_drive_letter_is_removed(path: str) -> None:
    """A colon is not a drive letter, and a path is not guessed at.

    ``C:`` on its own has no separator after it, so it is not the prefix of a
    Unix path — it is something this code does not understand, and inventing a
    path out of it would be worse than showing what arrived.
    """
    assert _normalise_path(path) == path.replace("\\", "/")
