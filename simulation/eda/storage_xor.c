/* Deposit an upset into one actual RTL variable bit without forcing
 * the target through any subsequent clock edge. X and Z are rejected. */
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <vpi_user.h>

static PLI_INT32 storage_xor(PLI_BYTE8 *unused)
{
    (void)unused;
    vpiHandle call = vpi_handle(vpiSysTfCall, NULL);
    vpiHandle args = vpi_iterate(vpiArgument, call);
    vpiHandle path_arg = args ? vpi_scan(args) : NULL;
    vpiHandle bit_arg = path_arg ? vpi_scan(args) : NULL;
    s_vpi_value value = {.format = vpiStringVal};
    vpiHandle target = NULL;
    int bit = -1;
    if (bit_arg) {
        vpi_get_value(path_arg, &value);
        target = vpi_handle_by_name(value.value.str, NULL);
        value.format = vpiIntVal;
        vpi_get_value(bit_arg, &value);
        bit = value.value.integer;
        vpi_free_object(args);
    }
    int before = -1;
    int width = target ? vpi_get(vpiSize, target) : 0;
    if (bit >= 0 && bit < width) {
        int count = (width + 31) / 32;
        s_vpi_vecval *words = calloc(count, sizeof(*words));
        if (words) {
            unsigned mask = UINT32_C(1) << (bit % 32);
            value.format = vpiVectorVal;
            vpi_get_value(target, &value);
            memcpy(words, value.value.vector, count * sizeof(*words));
            if (!(words[bit / 32].bval & mask)) {
                before = !!(words[bit / 32].aval & mask);
                words[bit / 32].aval ^= mask;
                value.value.vector = words;
                vpi_put_value(target, &value, NULL, vpiNoDelay);
                vpi_get_value(target, &value);
                if ((value.value.vector[bit / 32].bval & mask) ||
                    !!(value.value.vector[bit / 32].aval & mask) == before)
                    before = -1;
            }
            free(words);
        }
    }
    value.format = vpiIntVal;
    value.value.integer = before;
    vpi_put_value(call, &value, NULL, vpiNoDelay);
    return 0;
}

void register_storage_xor(void)
{
    s_vpi_systf_data task = {
        .type = vpiSysFunc,
        .sysfunctype = vpiIntFunc,
        .tfname = "$tage_storage_xor",
        .calltf = storage_xor,
    };
    vpi_register_systf(&task);
}
