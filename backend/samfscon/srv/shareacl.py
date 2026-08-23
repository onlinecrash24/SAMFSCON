"""The share-level security descriptor, over srvsvc.

Level 502 of ``NetShareGetInfo`` carries a share's descriptor in ``sd_buf`` as
a marshalled blob rather than as a structure — so it is unpacked with
``ndr_unpack`` and packed again to write it. That is the only thing separating
this module from :mod:`samfscon.srv.acl`, which does all the actual work.

Worth knowing before editing one: on most Samba installations the share
descriptor grants Everyone full control and the file permissions do the real
work. That is not a misconfiguration, it is the usual arrangement — the share
permission is a ceiling, not a policy — and tightening it here is a blunt
instrument that applies to the whole share at once, including to the
administrators who will later wonder why they cannot get in.
"""

from __future__ import annotations

import logging

from samfscon.core.errors import NotFound, SamfsconError, translate
from samfscon.srv import acl
from samfscon.srv.connection import ServerConnection

logger = logging.getLogger(__name__)

# What Samba hands back for a share nobody has set a descriptor on: full
# control for Everyone, which is the default the file permissions then bound.
DEFAULT_SDDL = "D:(A;;FA;;;WD)"


def read(conn: ServerConnection, share: str) -> acl.SecurityDescriptor:
    """The share's descriptor, parsed.

    A share with no descriptor at all is not an error and does not deserve an
    empty editor: it means "no restriction here", and the default is rendered
    so the editor opens on what the server actually enforces.

    A descriptor that is *there* and could not be read is a different thing
    entirely, and it used to be rendered as the same default — which is
    "could not determine" reported as "is not restricted", in the widest
    direction there is. Worse than a wrong screen: the editor writes back what
    it shows, so saving any change would have replaced a real descriptor with
    a fabricated Everyone-full-control that nobody ever saw.

    It raises now, the way the file-level reader beside it already did.
    """
    try:
        info = conn.srvsvc.NetShareGetInfo(None, share, 502)
    except Exception as exc:
        error = translate(exc)
        if error.status_code == 404:
            raise NotFound(
                "The share does not exist on this server.",
                code="share_not_found",
                context={"share": share},
            ) from exc
        raise error from exc

    sddl = _sddl_from(info)
    if sddl is None:
        logger.debug("share %s carries no security descriptor; using the default", share)
        sddl = DEFAULT_SDDL

    return acl.parse(sddl)


def write(conn: ServerConnection, share: str, sddl: str) -> None:
    """Replace the share's descriptor.

    Level 1501 rather than 502: it carries the descriptor and nothing else, so
    a permission change cannot disturb the path or the comment on its way
    through. Writing 502 back would mean re-sending every other field and
    trusting that what was read a moment ago is still current.
    """
    from samba.dcerpc import srvsvc
    from samba.ndr import ndr_pack

    # Parsed against the domain the server names, not against BUILTIN. A share
    # descriptor is the one people are most likely to paste in from
    # `net rpc share getsecurity`, and its output can carry DA — see
    # acl.to_descriptor for what that costs when the domain is guessed.
    descriptor = acl.to_descriptor(conn, sddl)

    info = srvsvc.sec_desc_buf()
    packed = ndr_pack(descriptor)
    info.sd = descriptor
    info.sd_size = len(packed)

    from samfscon.srv.shares import share_info

    pipe = conn.srvsvc
    wrapped = share_info(1501, info)
    errors: list[str] = []
    for attempt in (
        lambda: pipe.NetShareSetInfo(None, share, 1501, wrapped, 0),
        lambda: pipe.NetShareSetInfo(None, share, 1501, wrapped, None),
        lambda: pipe.NetShareSetInfo(None, share, 1501, info, 0),
    ):
        try:
            attempt()
            logger.info("share permissions changed: %s", share)
            return
        except TypeError as exc:
            errors.append(str(exc))
            continue
        except Exception as exc:
            raise translate(exc) from exc

    raise SamfsconError(
        "The share's permissions could not be written.",
        code="srvsvc_unsupported",
        detail="; ".join(errors),
        hint="Samba's NetShareSetInfo has an unexpected signature in this build.",
    )


def _sddl_from(info: object) -> str | None:
    """Pull the SDDL out of a level-502 reply, whatever shape it arrived in.

    ``sd_buf`` is a marshalled blob on some builds and an already-unpacked
    descriptor on others. Both are handled rather than one assumed, because
    which one it is depends on the Samba version rather than on anything this
    code can control.

    Returns ``None`` for a share that carries no descriptor, and *raises* for
    one that carries something this code could not read. Those two used to be
    the same answer, and the caller turned both into Everyone-full-control.
    """
    buffer = getattr(info, "sd_buf", None)
    if buffer is None:
        return None

    descriptor = getattr(buffer, "sd", buffer)
    if descriptor is None:
        return None

    # Already a descriptor object.
    renderer = getattr(descriptor, "as_sddl", None)
    if callable(renderer):
        try:
            return renderer()
        except Exception as exc:
            # Not a fall-through any more. If it renders at all this is the
            # call that renders it; a failure here is a descriptor we cannot
            # read, and the unpack path below is for a different shape, not
            # for a second attempt at this one.
            raise _unreadable(exc) from exc

    if isinstance(descriptor, (bytes, bytearray)):
        try:
            from samba.dcerpc import security
            from samba.ndr import ndr_unpack

            return ndr_unpack(security.descriptor, bytes(descriptor)).as_sddl()
        except Exception as exc:
            raise _unreadable(exc) from exc

    # Neither renderable nor bytes: a shape nobody here anticipated. Reporting
    # it as "no descriptor" would be inventing the most permissive answer out
    # of not knowing.
    raise _unreadable(TypeError(f"sd_buf carried a {type(descriptor).__name__}"))


def _unreadable(cause: BaseException) -> SamfsconError:
    return SamfsconError(
        "The security descriptor could not be rendered.",
        code="sddl_unrenderable",
        detail=str(cause),
        hint=(
            "The share has one and this console could not read it. It is not "
            "shown as unrestricted, because saving that would replace it. "
            "`net rpc share getsecurity` on the server prints the same "
            "descriptor in a form that can be compared."
        ),
    )
