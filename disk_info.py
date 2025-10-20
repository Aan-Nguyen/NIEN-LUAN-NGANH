import psutil
import wmi
import json
import re

def format_size(bytes_size):
    if bytes_size is None:
        return "0 B"
    size = float(bytes_size)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"

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
        disk_name = disk.DeviceID.split("\\")[-1]
        model = disk.Model or "Unknown"
        vendor = extract_vendor(model)
        serial = getattr(disk, "SerialNumber", "").strip()
        protocol = get_protocol(disk)
        size_bytes = int(disk.Size) if disk.Size else 0

        volumes = []
        raw_path_disk = ""
        for partition in disk.associators("Win32_DiskDriveToDiskPartition"):
            try:
                part_index = int(getattr(partition, "Index", -1))
            except Exception:
                part_index = -1

            for logical in partition.associators("Win32_LogicalDiskToPartition"):
                drive_letter = logical.DeviceID
                usage = None
                try:
                    usage = psutil.disk_usage(drive_letter + "\\")
                except (PermissionError, FileNotFoundError, OSError):
                    usage = None

                raw_path = f"\\\\.\\{drive_letter}"
                raw_path_disk = raw_path if not raw_path_disk else raw_path_disk

                volumes.append({
                    "letter": drive_letter.replace("\\", "/"),
                    "label": logical.VolumeName or "",
                    "filesystem": logical.FileSystem or "",
                    "size": format_size(usage.total) if usage else "0 B",
                    "free": format_size(usage.free) if usage else "0 B",
                    "offset": int(getattr(partition, "StartingOffset", 0)),
                    "path": raw_path,
                    "partition_index": part_index
                })

        disks.append({
            "name": disk_name.upper(),
            "vendor": vendor,
            "model": model.strip(),
            "serial": serial,
            "protocol": protocol.strip(),
            "size": format_size(size_bytes),
            "path": raw_path_disk,
            "index": d_index,
            "volumes": volumes
        })

    return {"disks": disks}

if __name__ == "__main__":
    info = get_disk_info()
    with open("disk_info.json", "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2, ensure_ascii=False)

    print(json.dumps(info, indent=2, ensure_ascii=False))
