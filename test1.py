import struct, os, json
from datetime import datetime, timedelta

# --- CONFIG ---
DRIVE = r"\\.\F:"   # Phân vùng FAT32
OUT_DIR = r"C:\NLN\code\Machine-Learning-Forensic-Application"

# --- UTIL ---
def fat_time(date, time, tenth=0):
    if date == 0: return ""
    y, m, d = ((date >> 9) & 0x7F) + 1980, (date >> 5) & 0x0F, date & 0x1F
    h, mi, s = (time >> 11) & 0x1F, (time >> 5) & 0x3F, (time & 0x1F) * 2
    try:
        dt = datetime(y, m, d, h, mi, s) + timedelta(milliseconds=tenth * 10)
        return dt.strftime("%d/%m/%Y %H:%M:%S")
    except: return "Invalid"

def read_sector(f, sector, size=512):
    f.seek(sector * size)
    return f.read(size)

def parse_bpb(bs):
    return {
        "bps": struct.unpack("<H", bs[11:13])[0],
        "spc": bs[13],
        "res": struct.unpack("<H", bs[14:16])[0],
        "nf": bs[16],
        "spf": struct.unpack("<I", bs[36:40])[0],
        "root": struct.unpack("<I", bs[44:48])[0]
    }

def layout(bpb):
    fat = bpb["res"]
    data = fat + bpb["nf"] * bpb["spf"]
    return {"fat": fat, "data": data}

def first_sector(cluster, bpb, lay):
    return lay["data"] + (cluster - 2) * bpb["spc"]

def read_fat_entry(f, clus, bpb, lay):
    if clus < 2: return None
    off = lay["fat"] * bpb["bps"] + clus * 4
    try:
        f.seek(off); val = struct.unpack("<I", f.read(4))[0] & 0x0FFFFFFF
        return val
    except: return None

def parse_dir(data):
    entries, lfn = [], []
    for i in range(0, len(data), 32):
        e = data[i:i+32]
        if len(e) < 32 or e[0] == 0x00: break
        attr = e[11]
        if attr == 0x0F:
            lfn.insert(0, (e[1:11] + e[14:26] + e[28:32]).decode("utf-16le", "ignore"))
            continue
        deleted = e[0] == 0xE5
        name8 = e[0:8].decode("ascii", "replace").strip()
        ext = e[8:11].decode("ascii", "replace").strip()
        name = "".join(lfn).split("\x00")[0] if lfn else f"{name8}.{ext}" if ext else name8
        lfn = []
        clus = (struct.unpack("<H", e[20:22])[0] << 16) | struct.unpack("<H", e[26:28])[0]
        size = struct.unpack("<I", e[28:32])[0]
        entries.append({
            "name": name, "deleted": deleted, "attr": attr, "clus": clus, "size": size,
            "crt_d": struct.unpack("<H", e[16:18])[0], "crt_t": struct.unpack("<H", e[14:16])[0],
            "tenth": e[13], "mod_d": struct.unpack("<H", e[24:26])[0],
            "mod_t": struct.unpack("<H", e[22:24])[0], "acc_d": struct.unpack("<H", e[18:20])[0],
            "ext": ext.lower()
        })
    return entries

def check_status(f, clus, size, bpb, lay):
    cs = bpb["bps"] * bpb["spc"]
    need = (size + cs - 1) // cs
    free = 0
    for i in range(need):
        val = read_fat_entry(f, clus + i, bpb, lay)
        if val == 0: free += 1
    if free == need: return "Recoverable"
    if free == 0: return "Overwritten"
    return "Partially Recoverable"

def scan_dir(f, clus, bpb, lay, path=""):
    f.seek(first_sector(clus, bpb, lay) * bpb["bps"])
    data = f.read(bpb["bps"] * bpb["spc"])
    results = []
    for e in parse_dir(data):
        full = os.path.join(path, e["name"])
        if e["deleted"] and e["clus"] > 1:
            results.append({
                "name": e["name"], "type": e["ext"], "size": e["size"],
                "created": fat_time(e["crt_d"], e["crt_t"], e["tenth"]),
                "modified": fat_time(e["mod_d"], e["mod_t"]),
                "accessed": fat_time(e["acc_d"], 0),
                "full_path": full,
                "offset": first_sector(e["clus"], bpb, lay) * bpb["bps"],
                "start_cluster": e["clus"],
                "status": check_status(f, e["clus"], e["size"], bpb, lay)
            })
        if (e["attr"] & 0x10) and not e["deleted"] and e["clus"] > 1:
            results.extend(scan_dir(f, e["clus"], bpb, lay, full))
    return results

# --- MAIN ---
def main():
    with open(DRIVE, "rb") as f:
        boot = read_sector(f, 0)
        if boot[510:512] != b"\x55\xaa":
            print("❌ Không phải phân vùng FAT32 hợp lệ.")
            return
        bpb, lay = parse_bpb(boot), layout(parse_bpb(boot))
        files = scan_dir(f, bpb["root"], bpb, lay, "")
        out = os.path.join(OUT_DIR, "fat32_deleted_files.json")
        os.makedirs(OUT_DIR, exist_ok=True)
        with open(out, "w", encoding="utf-8") as j:
            json.dump(files, j, indent=4, ensure_ascii=False)
        print(f"✅ Đã lưu kết quả: {out}")

if __name__ == "__main__":
    main()
