from sys import version_info

from cffi import FFI

if version_info.major < 3:
    raise RuntimeError('Python 2 is unsupported')

ffibuilder = FFI()
ffibuilder.set_source('_freeipmi', r"""
#include <freeipmi/api/ipmi-api.h>
#include <freeipmi/api/ipmi-sensor-cmds-api.h>
#include <freeipmi/cmds/ipmi-sensor-cmds.h>
#include <freeipmi/record-format/ipmi-sdr-record-format.h>

#include <freeipmi/fiid/fiid.h>

fiid_obj_t boringipmi_test (ipmi_ctx_t ctx)
{
    fiid_obj_t f = fiid_obj_create(tmpl_cmd_get_device_sdr_rs);
    int err = ipmi_cmd_get_device_sdr(
            ctx,
            0,
            0,
            0,
            0xff,
            f
    );
    return f;
}
""", libraries=['freeipmi'])

ffibuilder.cdef("""
typedef struct ipmi_ctx *ipmi_ctx_t;

int ipmi_ctx_errnum (ipmi_ctx_t ctx);
char *ipmi_ctx_errormsg (ipmi_ctx_t ctx);

ipmi_ctx_t ipmi_ctx_create (void);
int ipmi_ctx_close (ipmi_ctx_t ctx);
void ipmi_ctx_destroy (ipmi_ctx_t ctx);

int ipmi_ctx_open_outofband_2_0 (ipmi_ctx_t ctx,
                                 const char *hostname,
                                 const char *username,
                                 const char *password,
                                 const unsigned char *k_g,
                                 unsigned int k_g_len,
                                 uint8_t privilege_level,
                                 uint8_t cipher_suite_id,
                                 unsigned int session_timeout,
                                 unsigned int retransmission_timeout,
                                 unsigned int workaround_flags,
                                 unsigned int flags);

/*  FIID  */
/* this is here so it will resolve the type of fiid_err */
enum fiid_err
  {
    FIID_ERR_SUCCESS                         =  0,
    FIID_ERR_OBJ_NULL                        =  1,
    FIID_ERR_OBJ_INVALID                     =  2,
    FIID_ERR_ITERATOR_NULL                   =  3,
    FIID_ERR_ITERATOR_INVALID                =  4,
    FIID_ERR_PARAMETERS                      =  5,
    FIID_ERR_TEMPLATE_INVALID                =  6,
    FIID_ERR_FIELD_NOT_FOUND                 =  7,
    FIID_ERR_KEY_INVALID                     =  8,
    FIID_ERR_FLAGS_INVALID                   =  9,
    FIID_ERR_TEMPLATE_NOT_BYTE_ALIGNED       = 10,
    FIID_ERR_FIELD_NOT_BYTE_ALIGNED          = 11,
    FIID_ERR_BLOCK_NOT_BYTE_ALIGNED          = 12,
    FIID_ERR_OVERFLOW                        = 13,
    FIID_ERR_MAX_FIELD_LEN_MISMATCH          = 14,
    FIID_ERR_KEY_FIELD_MISMATCH              = 15,
    FIID_ERR_FLAGS_FIELD_MISMATCH            = 16,
    FIID_ERR_TEMPLATE_LENGTH_MISMATCH        = 17,
    FIID_ERR_DATA_NOT_BYTE_ALIGNED           = 18,
    FIID_ERR_REQUIRED_FIELD_MISSING          = 19,
    FIID_ERR_FIXED_LENGTH_FIELD_INVALID      = 20,
    FIID_ERR_DATA_NOT_AVAILABLE              = 21,
    FIID_ERR_NOT_IDENTICAL                   = 22,
    FIID_ERR_OUT_OF_MEMORY                   = 23,
    FIID_ERR_INTERNAL_ERROR                  = 24,
    FIID_ERR_ERRNUMRANGE                     = 25
  };
typedef enum fiid_err fiid_err_t;

typedef struct fiid_obj *fiid_obj_t;

typedef struct fiid_field
{
  unsigned int max_field_len;
  char key[256];  // FIID_FIELD_MAX_KEY_LEN
  unsigned int flags;
} fiid_field_t;

typedef fiid_field_t fiid_template_t[];

fiid_err_t fiid_obj_errnum (fiid_obj_t obj);
char *fiid_obj_errormsg (fiid_obj_t obj);

fiid_obj_t fiid_obj_create (fiid_template_t tmpl);
void fiid_obj_destroy (fiid_obj_t obj);

int fiid_obj_field_len_bytes (fiid_obj_t obj, const char *field);

int FIID_OBJ_GET (fiid_obj_t obj, const char *field, uint64_t *val);
int fiid_obj_get_data (fiid_obj_t obj,
                       const char *field,
                       void *data,
                       unsigned int data_len);
int fiid_obj_set_all (fiid_obj_t obj, const void *data, unsigned int data_len);


/*  Commands  */
extern fiid_template_t tmpl_cmd_get_device_sdr_rs;

int ipmi_cmd_get_device_sdr (ipmi_ctx_t ctx,
    uint16_t reservation_id,
    uint16_t record_id,
    uint8_t offset_into_record,
    uint8_t bytes_to_read,
    fiid_obj_t obj_cmd_rs);


/*  Deserialization  */
extern fiid_template_t tmpl_sdr_record_header;

fiid_obj_t boringipmi_test(ipmi_ctx_t ctx);
""")

if __name__ == '__main__':
    ffibuilder.compile(verbose=True)
