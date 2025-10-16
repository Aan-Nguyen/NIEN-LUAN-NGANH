import psutil
import wmi
import json
import re

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
    elif iface in ["IDE", "SCSI", "SAS"] or "USB" in iface or "USB" in model or "USB" in pnp:
        return "USB"
    else:
        return "Unknown"

def get_disk_info():
    c = wmi.WMI()
    disks = []

    for d_index, disk in enumerate(c.Win32_DiskDrive()):
        disk_name = disk.DeviceID.split("\\")[-1]  # Ví dụ: PhysicalDrive0
        model = disk.Model or "Unknown"
        vendor = extract_vendor(model)
        serial = getattr(disk, "SerialNumber", "").strip()
        protocol = get_protocol(disk)
        size_gb = round(int(disk.Size) / (1024**3), 2) if disk.Size else 0.0

        volumes = []
        for p_index, partition in enumerate(disk.associators("Win32_DiskDriveToDiskPartition")):
            for logical in partition.associators("Win32_LogicalDiskToPartition"):
                path = f"\\\\.\\{logical.DeviceID.replace(':', '')}"  # \\.\C:
                letter = logical.DeviceID.replace("\\", "/")

                # Xử lý lỗi PermissionError
                try:
                    usage = psutil.disk_usage(logical.DeviceID + "\\")
                    total = round(usage.total / (1024**3), 2)
                    free = round(usage.free / (1024**3), 2)
                except (PermissionError, FileNotFoundError, OSError):
                    total = 0.0
                    free = 0.0

                volumes.append({
                    "letter": letter,
                    "label": logical.VolumeName or "",
                    "filesystem": logical.FileSystem or "",
                    "size_gb": total,
                    "free_gb": free,
                    "offset": int(partition.StartingOffset),
                    "path": path,
                    "partition_index": p_index
                })

        disks.append({
            "name": disk_name.upper(),
            "vendor": vendor,
            "model": model.strip(),
            "serial": serial,
            "protocol": protocol.strip(),
            "size_gb": size_gb,
            "path": f"\\\\.\\{disk_name}",   # thêm path cho ổ đĩa
            "index": d_index,
            "volumes": volumes
        })

    return {"disks": disks}

if __name__ == "__main__":
    info = get_disk_info()

    with open("disk_info.json", "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2, ensure_ascii=False)

    print(json.dumps(info, indent=2, ensure_ascii=False))
