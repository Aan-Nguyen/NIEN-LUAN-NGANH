import sys, os, json, re, psutil, wmi
from utils import format_size

def extract_vendor(model):
    if not model:
        return "Unknown"
    parts = re.split(r"\s+", model.strip())
    if len(parts) > 0:
        if parts[0].upper() in ["NVME", "USB"]:
            return parts[0].upper()
        return parts[0]
    return "Unknown"

def get_protocol(disk):
    iface = (disk.InterfaceType or "").upper()
    model = (disk.Model or "").upper()
    pnp = getattr(disk, "PNPDeviceID", "").upper()

    if "NVME" in model:
        return "NVMe"
    elif "USB" in iface or "USB" in model or "USB" in pnp:
        return "USB"
    elif iface in ["IDE", "SCSI", "SAS"]:
        return iface
    return "Unknown"

def safe_usage(path):
    try:
        return psutil.disk_usage(path)
    except Exception:
        return None

def get_disk_info():
    c = wmi.WMI()
    disks = []

    for disk in c.Win32_DiskDrive():
        device_id = disk.DeviceID or ""
        # Lấy số thật từ chuỗi "\\.\PHYSICALDRIVEX"
        match = re.search(r"PhysicalDrive(\d+)", device_id, re.I)
        d_index = int(match.group(1)) if match else -1
        disk_name = f"PhysicalDrive{d_index}" if d_index >= 0 else "UnknownDrive"
        model = (disk.Model or "Unknown").strip()
        vendor = extract_vendor(model)
        serial = (getattr(disk, "SerialNumber", "") or "").strip()
        protocol = get_protocol(disk)
        size_bytes = int(disk.Size) if getattr(disk, "Size", None) else 0

        volumes = []
        for partition in disk.associators("Win32_DiskDriveToDiskPartition") or []:
            for logical in partition.associators("Win32_LogicalDiskToPartition") or []:
                drive_letter = getattr(logical, "DeviceID", None)
                if not drive_letter:
                    continue  # bỏ volume không có tên (không có ký tự ổ)

                usage = safe_usage(drive_letter + "\\")
                raw_path = f"\\\\.\\{drive_letter.strip()}"
                volumes.append({
                    "letter": drive_letter.strip(),
                    "label": getattr(logical, "VolumeName", "") or "",
                    "filesystem": getattr(logical, "FileSystem", "") or "",
                    "size": format_size(usage.total) if usage else "0 B",
                    "free": format_size(usage.free) if usage else "0 B",
                    "offset": int(getattr(partition, "StartingOffset", 0) or 0),
                    "path": raw_path,
                    "partition_index": int(getattr(partition, "Index", -1))
                })

        # Bỏ ổ không có logical volumes (tức là toàn bộ volumes đều không có letter)
        if not volumes:
            continue

        disks.append({
            "name": disk_name,
            "vendor": vendor,
            "model": model,
            "serial": serial,
            "protocol": protocol,
            "size": format_size(size_bytes),
            "path": f"\\\\.\\PhysicalDrive{d_index}",
            "index": d_index,
            "volumes": volumes
        })

    return {"disks": disks}

if __name__ == "__main__":
    info = get_disk_info()
    with open("disk_info.json", "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2, ensure_ascii=False)
    print(json.dumps(info, indent=2, ensure_ascii=False))
