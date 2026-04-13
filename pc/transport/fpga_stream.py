from __future__ import annotations

import socket
from pathlib import Path
from typing import Dict, Iterator

from vision.virtual_source import FramePacket

from .protocol import HEADER_SIZE, HEADER_STRUCT, MAGIC, decode_packet, payload_to_frame


def _recv_exact(sock: socket.socket, size: int) -> bytes:
    chunks = []
    got = 0
    while got < size:
        part = sock.recv(size - got)
        if not part:
            raise ConnectionError("Socket closed while receiving packet")
        chunks.append(part)
        got += len(part)
    return b"".join(chunks)


class FpgaTcpSource:
    def __init__(self, host: str, port: int, timeout_s: float = 5.0) -> None:
        self.host = host
        self.port = int(port)
        self.timeout_s = float(timeout_s)

    def frames(self, max_frames: int) -> Iterator[FramePacket]:
        with socket.create_connection((self.host, self.port), timeout=self.timeout_s) as sock:
            sock.settimeout(self.timeout_s)

            for _ in range(max_frames):
                try:
                    header = _recv_exact(sock, HEADER_SIZE)
                except ConnectionError:
                    break
                unpacked = HEADER_STRUCT.unpack(header)
                if unpacked[0] != MAGIC:
                    raise ValueError("Invalid magic from FPGA stream")
                payload_len = int(unpacked[14])
                try:
                    payload = _recv_exact(sock, payload_len)
                except ConnectionError:
                    break
                packet = decode_packet(header + payload)
                frame = payload_to_frame(packet.width, packet.height, packet.channels, packet.payload)

                yield FramePacket(
                    frame=frame,
                    meta={
                        "index": packet.frame_id,
                        "gt_plate": "",
                        "gt_bbox": (packet.roi_x, packet.roi_y, packet.roi_w, packet.roi_h),
                        "source": "fpga_tcp",
                        "timestamp_ms": packet.timestamp_ms,
                    },
                )


class FpgaReplaySource:
    def __init__(self, stream_file: str) -> None:
        self.stream_file = Path(stream_file)

    def frames(self, max_frames: int) -> Iterator[FramePacket]:
        if not self.stream_file.exists():
            raise FileNotFoundError(f"Replay file not found: {self.stream_file}")

        with self.stream_file.open("rb") as f:
            count = 0
            while count < max_frames:
                header = f.read(HEADER_SIZE)
                if not header:
                    break
                if len(header) < HEADER_SIZE:
                    raise ValueError("Incomplete header in replay file")

                unpacked = HEADER_STRUCT.unpack(header)
                if unpacked[0] != MAGIC:
                    raise ValueError("Invalid magic in replay file")

                payload_len = int(unpacked[14])
                payload = f.read(payload_len)
                if len(payload) < payload_len:
                    raise ValueError("Incomplete payload in replay file")

                packet = decode_packet(header + payload)
                frame = payload_to_frame(packet.width, packet.height, packet.channels, packet.payload)

                yield FramePacket(
                    frame=frame,
                    meta={
                        "index": packet.frame_id,
                        "gt_plate": "",
                        "gt_bbox": (packet.roi_x, packet.roi_y, packet.roi_w, packet.roi_h),
                        "source": "fpga_replay",
                        "timestamp_ms": packet.timestamp_ms,
                    },
                )
                count += 1
