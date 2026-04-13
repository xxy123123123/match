from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
from typing import Tuple

import numpy as np


MAGIC = 0x45544C50  # 'PLTE' in little-endian memory order
PIXEL_GRAY8 = 0
PIXEL_BGR24 = 1

# <I B B H I Q H H B B H H H H I I
HEADER_STRUCT = struct.Struct("<IBBH IQHHBBHHHHII".replace(" ", ""))
HEADER_SIZE = HEADER_STRUCT.size


@dataclass
class FpgaPacket:
    version: int
    flags: int
    frame_id: int
    timestamp_ms: int
    width: int
    height: int
    channels: int
    pixel_format: int
    roi_x: int
    roi_y: int
    roi_w: int
    roi_h: int
    payload: bytes


def frame_to_payload(frame: np.ndarray) -> Tuple[int, int, int, bytes]:
    if frame.ndim == 2:
        h, w = frame.shape
        return w, h, 1, frame.tobytes()
    if frame.ndim == 3 and frame.shape[2] == 3:
        h, w, c = frame.shape
        return w, h, c, frame.tobytes()
    raise ValueError("Only GRAY8 or BGR24 frames are supported")


def payload_to_frame(width: int, height: int, channels: int, payload: bytes) -> np.ndarray:
    if channels == 1:
        arr = np.frombuffer(payload, dtype=np.uint8)
        return arr.reshape((height, width)).copy()
    if channels == 3:
        arr = np.frombuffer(payload, dtype=np.uint8)
        return arr.reshape((height, width, 3)).copy()
    raise ValueError(f"Unsupported channels: {channels}")


def encode_packet(packet: FpgaPacket) -> bytes:
    payload_len = len(packet.payload)
    crc32 = zlib.crc32(packet.payload) & 0xFFFFFFFF

    header = HEADER_STRUCT.pack(
        MAGIC,
        int(packet.version),
        HEADER_SIZE,
        int(packet.flags),
        int(packet.frame_id),
        int(packet.timestamp_ms),
        int(packet.width),
        int(packet.height),
        int(packet.channels),
        int(packet.pixel_format),
        int(packet.roi_x),
        int(packet.roi_y),
        int(packet.roi_w),
        int(packet.roi_h),
        payload_len,
        crc32,
    )
    return header + packet.payload


def decode_packet(raw: bytes) -> FpgaPacket:
    if len(raw) < HEADER_SIZE:
        raise ValueError("Packet too small")

    (
        magic,
        version,
        header_len,
        flags,
        frame_id,
        timestamp_ms,
        width,
        height,
        channels,
        pixel_format,
        roi_x,
        roi_y,
        roi_w,
        roi_h,
        payload_len,
        crc32,
    ) = HEADER_STRUCT.unpack(raw[:HEADER_SIZE])

    if magic != MAGIC:
        raise ValueError(f"Bad magic: {hex(magic)}")
    if header_len != HEADER_SIZE:
        raise ValueError(f"Unexpected header size: {header_len}")
    if len(raw) != HEADER_SIZE + payload_len:
        raise ValueError("Payload length mismatch")

    payload = raw[HEADER_SIZE:]
    calc_crc = zlib.crc32(payload) & 0xFFFFFFFF
    if calc_crc != crc32:
        raise ValueError("CRC mismatch")

    return FpgaPacket(
        version=version,
        flags=flags,
        frame_id=frame_id,
        timestamp_ms=timestamp_ms,
        width=width,
        height=height,
        channels=channels,
        pixel_format=pixel_format,
        roi_x=roi_x,
        roi_y=roi_y,
        roi_w=roi_w,
        roi_h=roi_h,
        payload=payload,
    )
