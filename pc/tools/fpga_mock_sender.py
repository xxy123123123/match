from __future__ import annotations

import argparse
import socket
import time
from pathlib import Path

from transport.protocol import FpgaPacket, PIXEL_BGR24, encode_packet, frame_to_payload
from vision.virtual_source import VirtualPlateSource


def main() -> None:
    parser = argparse.ArgumentParser(description="Mock FPGA sender over TCP")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5600)
    parser.add_argument("--frames", type=int, default=300)
    parser.add_argument("--fps", type=int, default=25)
    parser.add_argument("--save-stream", default="", help="Optional output .bin stream file path")
    args = parser.parse_args()

    source = VirtualPlateSource(
        width=1280,
        height=720,
        fps=args.fps,
        plate_pool=["粤B12345", "京A8K2P9", "沪C9M7N1"],
    )

    interval = 1.0 / max(args.fps, 1)
    stream_fp = None
    if args.save_stream:
        stream_path = Path(args.save_stream).resolve()
        stream_path.parent.mkdir(parents=True, exist_ok=True)
        stream_fp = stream_path.open("wb")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((args.host, args.port))
        server.listen(1)
        print(f"Mock sender listening on {args.host}:{args.port}")
        conn, addr = server.accept()
        with conn:
            print(f"Client connected: {addr}")
            for packet in source.frames(max_frames=args.frames):
                frame = packet.frame
                meta = packet.meta
                x, y, w, h = tuple(meta.get("gt_bbox", (0, 0, 0, 0)))
                width, height, channels, payload = frame_to_payload(frame)

                out = FpgaPacket(
                    version=1,
                    flags=0,
                    frame_id=int(meta.get("index", 0)),
                    timestamp_ms=int(time.time() * 1000),
                    width=width,
                    height=height,
                    channels=channels,
                    pixel_format=PIXEL_BGR24,
                    roi_x=int(x),
                    roi_y=int(y),
                    roi_w=int(w),
                    roi_h=int(h),
                    payload=payload,
                )
                raw = encode_packet(out)
                conn.sendall(raw)
                if stream_fp is not None:
                    stream_fp.write(raw)
                time.sleep(interval)

    if stream_fp is not None:
        stream_fp.close()
        print(f"Saved stream file: {stream_path}")

    print("Mock sender finished")


if __name__ == "__main__":
    main()
