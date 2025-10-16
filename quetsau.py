# quick_deleted_ntfs_with_offsets_bitmap.py
import pytsk3
import sys
import os
from datetime import datetime

def format_time(ts):
    if ts is None or ts == 0:
        return "N/A"
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")

def try_get_attr_runs(file_obj):
    """
    Trích các data runs (LCN, length) từ attribute mặc định nếu có.
    Trả về danh sách tuple (lcn_start, length_in_clusters)
    """
    runs_out = []

    # Một số phiên bản pytsk3 cho phép duyệt attributes qua file_obj
    try:
        for attr in file_obj:
            # chọn attribute dữ liệu mặc định (NTFS data)
            try:
                t = attr.info.type
            except Exception:
                t = None

            # Loại attr cho dữ liệu (NTFS data or default)
            if t in (pytsk3.TSK_FS_ATTR_TYPE_NTFS_DATA, pytsk3.TSK_FS_ATTR_TYPE_DEFAULT, None):
                # Một số phiên bản expose runlist trực tiếp
                runs = getattr(attr.info, "run", None) or getattr(attr.info, "runs", None)
                if runs:
                    # normalize
                    for r in runs:
                        # r có thể là object hoặc tuple
                        lcn = getattr(r, "addr", None) or getattr(r, "lcn", None)
                        length = getattr(r, "len", None) or getattr(r, "length", None)
                        # nếu tuple (lcn, length)
                        if lcn is None and isinstance(r, (tuple, list)) and len(r) >= 2:
                            lcn, length = r[0], r[1]
                        if lcn is None:
                            continue
                        runs_out.append((int(lcn), int(length) if length is not None else 0))
                    if runs_out:
                        break
                else:
                    # Thử cách khác: một số attr iterable yield run objects
                    try:
                        tmp = []
                        for r in attr:
                            lcn = getattr(r, "addr", None) or getattr(r, "lcn", None) or getattr(r, "start", None)
                            length = getattr(r, "len", None) or getattr(r, "length", None) or getattr(r, "count", None)
                            if lcn is not None:
                                tmp.append((int(lcn), int(length) if length is not None else 0))
                        if tmp:
                            runs_out = tmp
                            break
                    except Exception:
                        pass
    except Exception:
        pass

    return runs_out if runs_out else None

def read_ntfs_bitmap(fs):
    """
    Mở file $Bitmap và trả về bytes của bitmap.
    Trả về tuple (bitmap_bytes, cluster_count) hoặc (None, None) nếu không lấy được.
    """
    try:
        # $Bitmap is at root path "$Bitmap" or "/$Extend/$Bitmap" depending on implementation.
        # Try common paths:
        candidates = ["/$Bitmap", "/$Extend/$Bitmap", "/$Volume/$Bitmap"]
        bitmap_file = None
        for p in candidates:
            try:
                bitmap_file = fs.open(p)
                break
            except Exception:
                bitmap_file = None
                continue
        if bitmap_file is None:
            # Try opening by MFT name "$Bitmap"
            try:
                bitmap_file = fs.open("/$Bitmap")
            except Exception:
                return None, None

        size = bitmap_file.info.meta.size
        data = b""
        offset = 0
        CHUNK = 1024 * 1024
        while offset < size:
            toread = CHUNK if (size - offset) > CHUNK else (size - offset)
            chunk = bitmap_file.read_random(offset, toread)
            if not chunk:
                break
            data += chunk
            offset += len(chunk)
        # number of clusters represented = len(data) * 8
        return data, len(data) * 8
    except Exception:
        return None, None

def is_cluster_allocated(bitmap_bytes, lcn):
    """
    Kiểm tra bit lcn trong bitmap (bitmap_bytes).
    Trả về True nếu allocated (bit=1), False nếu free (bit=0).
    """
    if bitmap_bytes is None:
        return None
    byte_index = lcn // 8
    bit_index = lcn % 8
    if byte_index < 0 or byte_index >= len(bitmap_bytes):
        return None
    b = bitmap_bytes[byte_index]
    return True if ((b >> bit_index) & 1) else False

def determine_overwrite_status_from_runs(runs, bitmap_bytes):
    """
    runs: list of (lcn_start, length)
    bitmap_bytes: bytes of $Bitmap
    Trả về "Recoverable" / "Overwritten" / "Partially Recoverable" / "Unknown"
    """
    if not runs:
        return "Unknown"
    total_clusters = 0
    allocated_clusters = 0
    free_clusters = 0
    unknown_clusters = 0

    for (lcn_start, length) in runs:
        # if length==0, treat as unknown
        if length == 0:
            unknown_clusters += 1
            continue
        total_clusters += length
        for i in range(length):
            lcn = lcn_start + i
            alloc = is_cluster_allocated(bitmap_bytes, lcn)
            if alloc is None:
                unknown_clusters += 1
            elif alloc:
                allocated_clusters += 1
            else:
                free_clusters += 1

    # Decide
    if total_clusters == 0 and unknown_clusters > 0:
        return "Unknown"
    if unknown_clusters > 0 and allocated_clusters == 0 and free_clusters > 0:
        return "Partially Recoverable"
    if allocated_clusters == 0 and free_clusters > 0:
        return "Recoverable"
    if free_clusters == 0 and allocated_clusters > 0:
        return "Overwritten"
    if allocated_clusters > 0 and free_clusters > 0:
        return "Partially Recoverable"
    return "Unknown"

def scan_deleted_ntfs(image_path):
    """
    Quét nhanh các file bị xóa trên NTFS.
    Hiển thị kết quả ngay khi phát hiện, kèm size + MFT entry + data runs/offset.
    Dùng $Bitmap để xác định cluster allocated/free.
    """
    img = pytsk3.Img_Info(image_path)
    fs = pytsk3.FS_Info(img)
    count = 0

    # attempt to get block/cluster size for offset calc
    cluster_size = None
    try:
        cluster_size = getattr(fs.info, "block_size", None) or getattr(fs, "block_size", None)
    except Exception:
        cluster_size = None

    # read bitmap once
    bitmap_bytes, bitmap_cluster_count = read_ntfs_bitmap(fs)
    if bitmap_bytes is None:
        print("[!] Không đọc được $Bitmap — overwrite detection sẽ ít chính xác hơn.")

    def walk_dir(directory, parent_path="/"):
        nonlocal count
        for entry in directory:
            if not hasattr(entry, "info") or entry.info.name.name in [b".", b".."]:
                continue

            meta = entry.info.meta
            name = entry.info.name.name.decode(errors="ignore")
            full_path = os.path.join(parent_path, name)

            if meta and meta.flags & pytsk3.TSK_FS_META_FLAG_UNALLOC:
                # Size and MFT entry
                file_size = getattr(meta, "size", None)
                mft_entry = getattr(meta, "addr", None)

                # Lấy extension
                _, ext = os.path.splitext(name)
                ext = ext[1:] if ext else "N/A"

                # Kiểm tra ghi đè (best-effort; use bitmap+data runs)
                overwritten = "Unknown"

                # get runs
                runs_info = None
                try:
                    file_obj = None
                    try:
                        file_obj = entry.as_file()
                    except Exception:
                        file_obj = None
                    if file_obj:
                        runs_info = try_get_attr_runs(file_obj)
                except Exception:
                    runs_info = None

                # If we have runs and bitmap, determine status
                if runs_info and bitmap_bytes:
                    overwritten = determine_overwrite_status_from_runs(runs_info, bitmap_bytes)
                else:
                    # fallback heuristic:
                    # if no runs -> Unknown
                    # if runs but no bitmap -> Unknown
                    overwritten = "Unknown"

                count += 1
                print(f"[{count}] {full_path}")
                print(f"     Type: {ext}")
                print(f"     Size (bytes): {file_size if file_size is not None else 'N/A'}")
                print(f"     MFT entry: {mft_entry if mft_entry is not None else 'N/A'}")
                if cluster_size:
                    print(f"     Cluster size: {cluster_size} bytes")
                if runs_info:
                    print("     Data runs (LCN clusters):")
                    for r in runs_info:
                        lcn = r[0]
                        ln = r[1]
                        off = (lcn * cluster_size) if (cluster_size and lcn is not None) else None
                        print(f"        LCN={lcn}, length_clusters={ln}, offset_bytes={off}")
                else:
                    print("     Data runs: (not available via pytsk3)")

                print(f"     Created:  {format_time(meta.crtime)}")
                print(f"     Modified: {format_time(meta.mtime)}")
                print(f"     Accessed: {format_time(meta.atime)}")
                print(f"     Overwritten DETECTION: {overwritten}\n")

            # Nếu là thư mục hợp lệ, đệ quy
            if meta and meta.type == pytsk3.TSK_FS_META_TYPE_DIR and not (meta.flags & pytsk3.TSK_FS_META_FLAG_UNALLOC):
                try:
                    subdir = entry.as_directory()
                    walk_dir(subdir, full_path)
                except Exception:
                    pass

    print(f"🔍 Đang quét phân vùng hoặc image: {image_path} ...\n")
    root_dir = fs.open_dir(path="/")
    walk_dir(root_dir)
    print(f"\n✅ Hoàn tất quét. Tổng số file bị xóa phát hiện: {count}")

if __name__ == "__main__":
    image_path = input(r"Nhập phân vùng hoặc file image (VD: \\.\E: hoặc C:\disk.img): ").strip()
    scan_deleted_ntfs(image_path)
