"""
lfs_insim/insim_packet_sender.py - Packet serialization.

`encode_packet()` is the single serialization route (validate + prepare +
pack): a pure function with no socket involved. Sending happens through
each client's InSimTransport (`client.send(packet)`), so this module holds
no connection state.
"""

import logging
import struct

from .exceptions import InSimPacketError
from .packets import ALLOWED_PACKETS, PacketFunctions

logger = logging.getLogger(__name__)

# Packet types whose send logs are muted.
# Empty by default; each module adds its own with mute_send_logs().
_MUTED_SEND_TYPES: set[str] = set()


def mute_send_logs(*packet_types: str) -> None:
    """Mute the send logs (DEBUG) for the given packet types."""
    _MUTED_SEND_TYPES.update(packet_types)


def unmute_send_logs(*packet_types: str) -> None:
    """Re-enable the send logs (DEBUG) for the given packet types."""
    _MUTED_SEND_TYPES.difference_update(packet_types)


def encode_packet(packet: PacketFunctions) -> bytes:
    """
    Serialize a packet into the exact bytes LFS expects.

    Validates that the packet type is sendable, runs prepare() (string
    padding to 4-byte blocks, Size update) and packs every field
    little-endian. Pure function: no socket involved.
    """
    # 1. Safety check: is this a packet LFS accepts from an InSim program?
    if type(packet) not in ALLOWED_PACKETS:
        raise InSimPacketError(
            f"Packet {type(packet).__name__} is not in the allowed-send list."
        )

    # 2. Preparation: adjust strings (multiples of 4) and update Size
    packet.prepare()

    # 3. Get the instance's actual format and pack
    fmt_string = packet.get_struct_string()

    pkt_name = type(packet).__name__
    _muted = pkt_name in _MUTED_SEND_TYPES
    values = _extract_values(packet)
    if not _muted:
        logger.debug(f"Packing {pkt_name} with fmt={fmt_string}")
        logger.debug(f"Values to pack: {values}")

    try:
        return struct.pack(fmt_string, *values)
    except Exception as e:
        raise InSimPacketError(
            f"Error packing {pkt_name}: {e}", packet_type=pkt_name
        ) from e


def _extract_values(obj):
    from dataclasses import fields

    extracted = []

    for f in fields(obj):
        fmt_meta = f.metadata.get("fmt")
        if fmt_meta is None:
            continue

        val = getattr(obj, f.name)

        # --- STRINGS ---
        # prepare()/validate_string_lengths() is the single layout authority
        # (P19): truncation and 4-byte padding already happened there. Here
        # we only encode; struct.pack null-pads fixed 'Ns' fields, and
        # variable strings resolve their format from len(val).
        if isinstance(val, str):
            # latin-1 is the LFS wire encoding (1 byte per char)
            extracted.append(val.encode("latin-1", "replace"))

        # --- VARIABLE LISTS AND TUPLES ---
        elif isinstance(fmt_meta, tuple):
            inner_fmt, limit = fmt_meta
            actual_items = val if val is not None else []

            # A string ('s', limit) was already handled above
            if inner_fmt == "s":
                pass
            else:
                # No padding here: process up to the declared limit
                # (limit None = purely variable, take everything).
                if limit is not None:
                    items_to_process = actual_items[:limit]
                else:
                    items_to_process = actual_items

                for item in items_to_process:
                    if hasattr(item, "get_fmt"):
                        extracted.extend(_extract_values(item))
                    elif isinstance(item, (tuple, list)):
                        # Multi-value item (e.g. an IP as (192,168,1,1) for '4B')
                        extracted.extend(item)
                    else:
                        extracted.append(item)

        # --- FIXED-FORMAT SEQUENCES (repeat(...): one fmt per slot) ---
        # The struct format always expands to the full fixed length, so the
        # value list must too: missing slots are padded with defaults.
        elif isinstance(fmt_meta, list):
            items = list(val) if val is not None else []
            for i, slot_fmt in enumerate(fmt_meta):
                item = items[i] if i < len(items) else None
                if isinstance(slot_fmt, type):
                    # Sub-struct slot (e.g. CarHCP in ISP_HCP)
                    extracted.extend(
                        _extract_values(item if item is not None else slot_fmt())
                    )
                elif item is None:
                    extracted.append(0)
                elif hasattr(item, "value"):  # Enum
                    extracted.append(int(item.value))
                else:
                    extracted.append(item)

        # --- SUB-STRUCTS ---
        elif hasattr(val, "get_fmt"):
            extracted.extend(_extract_values(val))

        # --- PRIMITIVES (Enums become plain ints) ---
        else:
            if hasattr(val, "value"):  # Enum
                extracted.append(int(val.value))
            else:
                extracted.append(val)

    return extracted
