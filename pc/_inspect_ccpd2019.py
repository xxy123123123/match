import tarfile
from collections import Counter

p = r"D:\文档\ccpd\CCPD2019.tar.xz"

c1 = Counter()
c2 = Counter()
img_cnt = 0
member_cnt = 0
samples = []

with tarfile.open(p, "r:xz") as tf:
    for m in tf:
        member_cnt += 1
        name = m.name.replace("\\", "/")
        parts = [x for x in name.split("/") if x]
        if parts:
            c1[parts[0]] += 1
        if len(parts) >= 2:
            c2[f"{parts[0]}/{parts[1]}"] += 1
        if name.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".webp")):
            img_cnt += 1
            if len(samples) < 30:
                samples.append(name)

print("total_members=", member_cnt)
print("image_members=", img_cnt)
print("top_level:")
for k, v in c1.most_common(30):
    print(f"  {k}: {v}")
print("top_2_levels:")
for k, v in c2.most_common(60):
    print(f"  {k}: {v}")
print("sample_images:")
for s in samples:
    print("  " + s)
