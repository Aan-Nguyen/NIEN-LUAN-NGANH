
def format_size(size_bytes):
    """Chuyển kích thước byte sang KB, MB, GB, TB"""
    if size_bytes == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB")
    i = 0
    dbl_s = float(size_bytes)
    while dbl_s >= 1024 and i < len(size_name)-1:
        dbl_s /= 1024
        i += 1
    return f"{dbl_s:.2f} {size_name[i]}"
