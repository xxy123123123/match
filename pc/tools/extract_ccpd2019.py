from __future__ import annotations

import tarfile
import time
from pathlib import Path

SRC = Path(r"D:\文档\ccpd\CCPD2019.tar.xz")
DST = Path(r"D:\文档\ccpd\CCPD2019_extracted")


def main() -> None:
    if not SRC.exists():
        raise FileNotFoundError(f"Archive not found: {SRC}")

    DST.mkdir(parents=True, exist_ok=True)

    start = time.time()
    print(f"[INFO] start extracting: {SRC}", flush=True)
    print(f"[INFO] destination: {DST}", flush=True)

    count = 0
    with tarfile.open(SRC, "r:xz") as tf:
        for member in tf:
            tf.extract(member, path=DST)
            count += 1
            if count % 2000 == 0:
                elapsed = (time.time() - start) / 60.0
                print(f"[INFO] extracted {count} members, elapsed={elapsed:.1f} min", flush=True)

    total_min = (time.time() - start) / 60.0
    print(f"[DONE] extracted to: {DST}", flush=True)
    print(f"[DONE] total extracted members: {count}", flush=True)
    print(f"[DONE] total time: {total_min:.1f} min", flush=True)


if __name__ == "__main__":
    main()
