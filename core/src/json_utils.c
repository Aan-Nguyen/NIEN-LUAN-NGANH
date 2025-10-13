#include <stdio.h>
#include <stdlib.h>
#include "../include/disk_info.h"
#include "../include/json_util.h"
#include "cJSON.h"   // cần tải cJSON.h + cJSON.c nếu chưa có

int save_disk_info_to_json(const char *filename, const DiskList *list) {
    if (!list) return 0;

    cJSON *root = cJSON_CreateObject();
    cJSON *disks = cJSON_AddArrayToObject(root, "disks");

    for (int i = 0; i < list->count; i++) {
        DiskInfo *d = &list->disks[i];
        cJSON *dj = cJSON_CreateObject();
        cJSON_AddStringToObject(dj, "physical_name", d->physical_name);
        cJSON_AddStringToObject(dj, "model", d->model);
        cJSON_AddStringToObject(dj, "serial_number", d->serial_number);
        cJSON_AddStringToObject(dj, "vendor", d->vendor);
        cJSON_AddStringToObject(dj, "protocol", d->protocol);
        cJSON_AddNumberToObject(dj, "size_gb", d->size_gb);

        cJSON *vols = cJSON_AddArrayToObject(dj, "volumes");
        for (int j = 0; j < d->volume_count; j++) {
            VolumeInfo *v = &d->volumes[j];
            cJSON *vj = cJSON_CreateObject();
            cJSON_AddStringToObject(vj, "volume_letter", v->volume_letter);
            cJSON_AddStringToObject(vj, "filesystem", v->filesystem);
            cJSON_AddStringToObject(vj, "label", v->label);
            cJSON_AddStringToObject(vj, "type", v->type);
            cJSON_AddNumberToObject(vj, "total_size", (double)v->total_size);
            cJSON_AddNumberToObject(vj, "free_space", (double)v->free_space);
            cJSON_AddItemToArray(vols, vj);
        }
        cJSON_AddItemToArray(disks, dj);
    }

    char *jsonStr = cJSON_Print(root);
    FILE *f = fopen(filename, "w");
    if (!f) {
        cJSON_Delete(root);
        free(jsonStr);
        return 0;
    }
    fprintf(f, "%s", jsonStr);
    fclose(f);

    cJSON_Delete(root);
    free(jsonStr);
    return 1;
}
