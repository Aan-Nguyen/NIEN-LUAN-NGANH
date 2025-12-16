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
        # ... (Giữ nguyên phần lấy thông tin disk cơ bản) ...
        device_id = disk.DeviceID or ""
        match = re.search(r"PhysicalDrive(\d+)", device_id, re.I)
        d_index = int(match.group(1)) if match else -1
        disk_name = f"PhysicalDrive{d_index}" if d_index >= 0 else "UnknownDrive"
        model = (disk.Model or "Unknown").strip()
        vendor = extract_vendor(model)
        serial = (getattr(disk, "SerialNumber", "") or "").strip()
        protocol = get_protocol(disk)
        size_bytes = int(disk.Size) if getattr(disk, "Size", None) else 0

        volumes = []
        # Lặp qua các phân vùng vật lý
        partitions = disk.associators("Win32_DiskDriveToDiskPartition") or []
        
        # Sắp xếp phân vùng theo thứ tự Index
        partitions.sort(key=lambda x: int(getattr(x, "Index", -1)))

        for partition in partitions:
            partition_size = int(getattr(partition, "Size", 0) or 0)
            partition_index = int(getattr(partition, "Index", -1))
            starting_offset = int(getattr(partition, "StartingOffset", 0) or 0)
            
            # Cố gắng tìm Logical Disk (Ổ có ký tự C:, D:...)
            logical_disks = partition.associators("Win32_LogicalDiskToPartition") or []
            
            if logical_disks:
                # Trường hợp CÓ ký tự ổ đĩa (Phân vùng hiện)
                for logical in logical_disks:
                    drive_letter = getattr(logical, "DeviceID", "") # Ví dụ: "C:"
                    usage = safe_usage(drive_letter + "\\") if drive_letter else None
                    
                    volumes.append({
                        "letter": drive_letter,
                        "label": getattr(logical, "VolumeName", "") or "",
                        "filesystem": getattr(logical, "FileSystem", "") or "Unknown",
                        "size": format_size(usage.total) if usage else format_size(partition_size),
                        "free": format_size(usage.free) if usage else "Unknown",
                        "offset": starting_offset,
                        "path": f"\\\\.\\{drive_letter}" if drive_letter else "",
                        "partition_index": partition_index,
                        "type": "Logical"
                    })
            else:
                # Trường hợp KHÔNG có ký tự ổ đĩa (Phân vùng ẩn / Recovery / System)
                volumes.append({
                    "letter": "N/A", # Không có ký tự
                    "label": "Hidden/System/Recovery", # Hoặc lấy từ Type của partition nếu cần chi tiết hơn
                    "filesystem": "Unknown", # WMI partition không cung cấp FS, cần dùng module khác hoặc để Unknown
                    "size": format_size(partition_size),
                    "free": "Unknown", # Không thể check free space nếu không mount
                    "offset": starting_offset,
                    "path": f"Partition{partition_index}",
                    "partition_index": partition_index,
                    "type": getattr(partition, "Type", "Unknown") # Ví dụ: GPT: System, Basic Data...
                })

        # Bỏ đoạn check "if not volumes: continue" để lấy cả ổ cứng không có phân vùng nào (ổ mới mua chưa format)
        
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
