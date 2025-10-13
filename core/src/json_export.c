#define _CRT_SECURE_NO_WARNINGS
#include <stdio.h>
#include <windows.h>
#include <string.h>

#define MAX_VOLUMES 64

typedef struct {
    char device_path[MAX_PATH];   // \\?\Volume{GUID}
    char volume_name[MAX_PATH];   // C:
    char volume_label[MAX_PATH];  // Tên ổ đĩa
    char volume_type[64];         // Logical Volume / Partition
    char volume_fs[10];           // NTFS, FAT32...
    unsigned long long total_size;
    unsigned long long free_size;
} VolumeInfo;
typedef struct {
    char disk_name[MAX_PATH];
    char disk_model[64];
    char disk_serial[64];
    char disk_vendor[64];
    char disk_protocol[64];
    unsigned long long total_size;
    unsigned long long free_size;
} DiskInfo;
int main() {
    //LAY THONG TIN PHAN VUNG
    VolumeInfo v[MAX_VOLUMES];
    int stt_vol = 0;
    char volumeName[MAX_PATH];

    HANDLE hFind = FindFirstVolumeA(volumeName, MAX_PATH);
    if (hFind == INVALID_HANDLE_VALUE) {
        printf("Không thể liệt kê volume.\n");
        return 1;
    }

    do {
        if (stt_vol >= MAX_VOLUMES) break;

        // Ghi lại đường dẫn thiết bị
        strcpy_s(v[stt_vol].device_path, MAX_PATH, volumeName);

        // Lấy ký tự ổ (C:, D:, ...)
        char pathNames[MAX_PATH] = {0};
        DWORD pathLen = 0;
        if (GetVolumePathNamesForVolumeNameA(volumeName, pathNames, MAX_PATH, &pathLen) && pathLen > 0) {
            strcpy_s(v[stt_vol].volume_name, MAX_PATH, pathNames);
            strcpy_s(v[stt_vol].volume_type, 32, "Logical Volume");
        } else {
            strcpy_s(v[stt_vol].volume_name, MAX_PATH, "(no mount)");
            strcpy_s(v[stt_vol].volume_type, 32, "Partition");
        }

        // Lấy nhãn và hệ thống tập tin
        GetVolumeInformationA(
            volumeName,
            v[stt_vol].volume_label,
            MAX_PATH,
            NULL, NULL, NULL,
            v[stt_vol].volume_fs,
            sizeof(v[stt_vol].volume_fs)
        );

        // Lấy dung lượng
        ULARGE_INTEGER freeBytes, totalBytes;
        if (GetDiskFreeSpaceExA(pathNames, &freeBytes, &totalBytes, NULL)) {
            v[stt_vol].total_size = totalBytes.QuadPart;
            v[stt_vol].free_size = freeBytes.QuadPart;
        }

        stt_vol++;
    } while (FindNextVolumeA(hFind, volumeName, MAX_PATH));

    FindVolumeClose(hFind);

    // LAY THONG TIN O CUNG
    DiskInfo disks[100];
    int disk_count = 0;

    for (int i = 0; i < 25; i++) {
        char device_path[64];
        sprintf(device_path, "\\\\.\\PhysicalDrive%d", i);
        HANDLE h_drive = CreateFileA(device_path, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE, NULL, OPEN_EXISTING, 0, NULL);
        if (h_drive == INVALID_HANDLE_VALUE) continue;
        DiskInfo d = { 0 };
        sprintf(d.disk_name, "PhysicalDrive%d", i);
    }
    // In kết quả
    printf("\n== DANH SÁCH PHÂN VÙNG ==\n\n");
    for (int j = 0; j < stt_vol; j++) {
        printf("{\n");
        printf("  \"device_path\": \"%s\",\n", v[j].device_path);
        printf("  \"letter\": \"%s\",\n", v[j].volume_name);
        printf("  \"label\": \"%s\",\n", v[j].volume_label);
        printf("  \"filesystem\": \"%s\",\n", v[j].volume_fs);
        printf("  \"type\": \"%s\",\n", v[j].volume_type);
        printf("  \"size_gb\": %.2f,\n", (double)v[j].total_size / (1024 * 1024 * 1024));
        printf("  \"free_gb\": %.2f\n", (double)v[j].free_size / (1024 * 1024 * 1024));
        printf("}\n\n");
    }
    return 0;
}
