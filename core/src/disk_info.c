#define _CRT_SECURE_NO_WARNINGS
#include <stdio.h>
#include <windows.h>
#include <string.h>

#define MAX_VOLUMES 64
#define MAX_DISKS   32

typedef struct {
    char volume_letter[MAX_PATH];
    char filesystem[MAX_PATH];
    char label[MAX_PATH];
    char type[32];
    unsigned long long total_size;
    unsigned long long free_space;
    char device_path[MAX_PATH];
    double size_gb;
    unsigned long long offset_bytes;
    unsigned long long length_bytes;
} VolumeInfo;

typedef struct {
    char physical_name[64];
    char model[64];
    char serial_number[64];
    char vendor[64];
    char protocol[64];
    double size_gb;
    unsigned long long total_size;
    unsigned long long free_space;
    VolumeInfo* volumes;
    int volume_count;
} DiskInfo;

typedef struct {
    VolumeInfo vol;
    DWORD disk_index;
} VolumeLocation;

const char* GetBusTypeString(STORAGE_BUS_TYPE busType) {
    switch (busType) {
        case BusTypeNvme: return "NVME";
        case BusTypeUsb: return "USB";
        case BusTypeSata: return "SATA";
        case BusTypeScsi: return "SCSI";
        case BusTypeAta: return "ATA";
        default: return "Unknown";
    }
}

// void PrintDiskInfo(const DiskInfo* d) {
//     printf("=================================================================\n");
//     printf("O DIA: %s\n", d->physical_name);
//     printf("-----------------------------------------------------------------\n");
//     printf("  - Vendor         : %s\n", strlen(d->vendor) ? d->vendor : "N/A");
//     printf("  - Model          : %s\n", strlen(d->model) ? d->model : "N/A");
//     printf("  - Serial         : %s\n", strlen(d->serial_number) ? d->serial_number : "N/A");
//     printf("  - Protocol       : %s\n", d->protocol);
//     printf("  - Tong dung luong: %.2f GB (%llu bytes)\n", d->size_gb, d->total_size);
//     printf("  - Tong dung luong trong: %.2f GB (%llu bytes)\n", (double)d->free_space / (1024 * 1024 * 1024), d->free_space);
//     printf("  - Cac phan vung (%d):\n", d->volume_count);
//     for (int i = 0; i < d->volume_count; i++) {
//         const VolumeInfo* v = &d->volumes[i];
//         printf("    -> %-5s | %-12s | FS: %-8s | Size: %6.2f GB | Free: %6.2f GB | Offset: %llu\n",
//                strlen(v->volume_letter) ? v->volume_letter : "[-]",
//                v->label, v->filesystem,
//                v->size_gb, (double)v->free_space / (1024 * 1024 * 1024),
//                v->offset_bytes);
//     }
//     printf("=================================================================\n\n");
// }

void ExportToJson(DiskInfo* disks, int disk_count, const char* path) {
    FILE* f = fopen(path, "w");
    if (!f) return;

    fprintf(f, "{\n  \"disks\": [\n");
    for (int i = 0; i < disk_count; i++) {
        DiskInfo* d = &disks[i];
        fprintf(f, "    {\n");
        fprintf(f, "      \"name\": \"%s\",\n", d->physical_name);
        fprintf(f, "      \"vendor\": \"%s\",\n", d->vendor);
        fprintf(f, "      \"model\": \"%s\",\n", d->model);
        fprintf(f, "      \"serial\": \"%s\",\n", d->serial_number);
        fprintf(f, "      \"protocol\": \"%s\",\n", d->protocol);
        fprintf(f, "      \"size_gb\": %.2f,\n", d->size_gb);
        fprintf(f, "      \"volumes\": [\n");
        for (int j = 0; j < d->volume_count; j++) {
            VolumeInfo* v = &d->volumes[j];
            fprintf(f, "        {\n");
            fprintf(f, "          \"letter\": \"%s\",\n", v->volume_letter);
            fprintf(f, "          \"label\": \"%s\",\n", v->label);
            fprintf(f, "          \"filesystem\": \"%s\",\n", v->filesystem);
            fprintf(f, "          \"size_gb\": %.2f,\n", v->size_gb);
            fprintf(f, "          \"free_gb\": %.2f,\n", (double)v->free_space / (1024 * 1024 * 1024));
            fprintf(f, "          \"offset\": %llu\n", v->offset_bytes);
            fprintf(f, "        }%s\n", (j < d->volume_count - 1) ? "," : "");
        }
        fprintf(f, "      ]\n");
        fprintf(f, "    }%s\n", (i < disk_count - 1) ? "," : "");
    }
    fprintf(f, "  ]\n}\n");
    fclose(f);
}

int main() {
    VolumeLocation all_volumes[MAX_VOLUMES];
    int total_volumes = 0;
    char vol_name[MAX_PATH];
    HANDLE h_find = FindFirstVolumeA(vol_name, MAX_PATH);

    if (h_find != INVALID_HANDLE_VALUE) {
        do {
            if (total_volumes >= MAX_VOLUMES) break;
            memset(&all_volumes[total_volumes], 0, sizeof(VolumeLocation));
            all_volumes[total_volumes].disk_index = (DWORD)-1;

            strcpy_s(all_volumes[total_volumes].vol.device_path, MAX_PATH, vol_name);

            char path_names[MAX_PATH] = { 0 };
            DWORD path_names_size = 0;
            if (GetVolumePathNamesForVolumeNameA(vol_name, path_names, MAX_PATH, &path_names_size) && path_names_size > 0) {
                strcpy_s(all_volumes[total_volumes].vol.volume_letter, MAX_PATH, path_names);
                for (int j = 0; all_volumes[total_volumes].vol.volume_letter[j]; j++) {
                    if (all_volumes[total_volumes].vol.volume_letter[j] == '\\') {
                        all_volumes[total_volumes].vol.volume_letter[j] = '/';
                    }
                }
                strcpy_s(all_volumes[total_volumes].vol.type, 32, "Logical Volume");
            } else strcpy_s(all_volumes[total_volumes].vol.type, 32, "Partition");

            GetVolumeInformationA(vol_name,
                all_volumes[total_volumes].vol.label, MAX_PATH,
                NULL, NULL, NULL,
                all_volumes[total_volumes].vol.filesystem, MAX_PATH);

            ULARGE_INTEGER freeBytes, totalBytes;
            if (GetDiskFreeSpaceExA(all_volumes[total_volumes].vol.volume_letter, &freeBytes, &totalBytes, NULL)) {
                all_volumes[total_volumes].vol.total_size = totalBytes.QuadPart;
                all_volumes[total_volumes].vol.free_space = freeBytes.QuadPart;
                all_volumes[total_volumes].vol.size_gb = (double)totalBytes.QuadPart / (1024 * 1024 * 1024);
            }

            vol_name[strlen(vol_name) - 1] = '\0';
            HANDLE h_vol = CreateFileA(vol_name, 0, FILE_SHARE_READ | FILE_SHARE_WRITE, NULL, OPEN_EXISTING, 0, NULL);
            vol_name[strlen(vol_name)] = '\\';

            if (h_vol != INVALID_HANDLE_VALUE) {
                BYTE buffer[1024];
                PVOLUME_DISK_EXTENTS ext = (PVOLUME_DISK_EXTENTS)buffer;
                DWORD bytes = 0;
                if (DeviceIoControl(h_vol, IOCTL_VOLUME_GET_VOLUME_DISK_EXTENTS, NULL, 0, ext, sizeof(buffer), &bytes, NULL)
                    && ext->NumberOfDiskExtents > 0) {
                    all_volumes[total_volumes].disk_index = ext->Extents[0].DiskNumber;
                    all_volumes[total_volumes].vol.offset_bytes = ext->Extents[0].StartingOffset.QuadPart;
                    all_volumes[total_volumes].vol.length_bytes = ext->Extents[0].ExtentLength.QuadPart;
                }
                CloseHandle(h_vol);
            }

            total_volumes++;
        } while (FindNextVolumeA(h_find, vol_name, MAX_PATH));
        FindVolumeClose(h_find);
    }

    DiskInfo disks[MAX_DISKS];
    int disk_count = 0;

    for (int i = 0; i < 25; i++) {
        char device_path[64];
        sprintf(device_path, "\\\\.\\PhysicalDrive%d", i);
        HANDLE h_drive = CreateFileA(device_path, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE, NULL, OPEN_EXISTING, 0, NULL);
        if (h_drive == INVALID_HANDLE_VALUE) continue;

        DiskInfo d = { 0 };
        sprintf(d.physical_name, "PhysicalDrive%d", i);

        DWORD bytes;
        BYTE buffer[2048];
        STORAGE_PROPERTY_QUERY query = { StorageDeviceProperty, PropertyStandardQuery };
        if (DeviceIoControl(h_drive, IOCTL_STORAGE_QUERY_PROPERTY, &query, sizeof(query), buffer, sizeof(buffer), &bytes, NULL)) {
            STORAGE_DEVICE_DESCRIPTOR* desc = (STORAGE_DEVICE_DESCRIPTOR*)buffer;
            if (desc->VendorIdOffset && desc->VendorIdOffset < bytes) strcpy_s(d.vendor, 64, buffer + desc->VendorIdOffset);
            if (desc->ProductIdOffset && desc->ProductIdOffset < bytes) strcpy_s(d.model, 64, buffer + desc->ProductIdOffset);
            if (desc->SerialNumberOffset && desc->SerialNumberOffset < bytes) strcpy_s(d.serial_number, 64, buffer + desc->SerialNumberOffset);
            strcpy_s(d.protocol, 64, GetBusTypeString(desc->BusType));
        }

        DISK_GEOMETRY_EX geo;
        if (DeviceIoControl(h_drive, IOCTL_DISK_GET_DRIVE_GEOMETRY_EX, NULL, 0, &geo, sizeof(geo), &bytes, NULL)) {
            d.total_size = geo.DiskSize.QuadPart;
            d.size_gb = (double)d.total_size / (1024 * 1024 * 1024);
        }

        int vcount = 0;
        for (int j = 0; j < total_volumes; j++)
            if (all_volumes[j].disk_index == i) vcount++;

        if (vcount > 0) {
            d.volume_count = vcount;
            d.volumes = (VolumeInfo*)malloc(sizeof(VolumeInfo) * vcount);
            d.free_space = 0;
            int idx = 0;
            for (int j = 0; j < total_volumes; j++) {
                if (all_volumes[j].disk_index == i) {
                    memcpy(&d.volumes[idx], &all_volumes[j].vol, sizeof(VolumeInfo));
                    d.free_space += all_volumes[j].vol.free_space;
                    idx++;
                }
            }
        }

        disks[disk_count++] = d;
        CloseHandle(h_drive);
    }

    for (int i = 0; i < disk_count; i++) PrintDiskInfo(&disks[i]);

    ExportToJson(disks, disk_count, "../output/disk_info.json");
    printf("Da luu ket qua tai: output/disk_info.json\n");

    for (int i = 0; i < disk_count; i++)
        if (disks[i].volumes) free(disks[i].volumes);

    printf("Quet hoan tat.\n");
    return 0;
}
