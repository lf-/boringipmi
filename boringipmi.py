from _freeipmi import ffi, lib

#define FIID_FIELD_REQUIRED         0x00000001
#define FIID_FIELD_OPTIONAL         0x00000002
#define FIID_FIELD_REQUIRED_MASK    0x0000000F
#define FIID_FIELD_LENGTH_FIXED     0x00000010
#define FIID_FIELD_LENGTH_VARIABLE  0x00000020
#define FIID_FIELD_LENGTH_MASK      0x000000F0
#define FIID_FIELD_MAKES_PACKET_SUFFICIENT 0x00010000

IPMI_ERROR = {
    0: 'IPMI_ERR_SUCCESS',
    1: 'IPMI_ERR_CTX_NULL',
    2: 'IPMI_ERR_CTX_INVALID',
    3: 'IPMI_ERR_PERMISSION',
    4: 'IPMI_ERR_USERNAME_INVALID',
    5: 'IPMI_ERR_PASSWORD_INVALID',
    6: 'IPMI_ERR_K_G_INVALID',
    7: 'IPMI_ERR_PRIVILEGE_LEVEL_INSUFFICIENT',
    8: 'IPMI_ERR_PRIVILEGE_LEVEL_CANNOT_BE_OBTAINED',
    9: 'IPMI_ERR_AUTHENTICATION_TYPE_UNAVAILABLE',
    10: 'IPMI_ERR_CIPHER_SUITE_ID_UNAVAILABLE',
    11: 'IPMI_ERR_PASSWORD_VERIFICATION_TIMEOUT',
    12: 'IPMI_ERR_IPMI_2_0_UNAVAILABLE',
    13: 'IPMI_ERR_CONNECTION_TIMEOUT',
    14: 'IPMI_ERR_SESSION_TIMEOUT',
    15: 'IPMI_ERR_DEVICE_ALREADY_OPEN',
    16: 'IPMI_ERR_DEVICE_NOT_OPEN',
    17: 'IPMI_ERR_DEVICE_NOT_SUPPORTED',
    18: 'IPMI_ERR_DEVICE_NOT_FOUND',
    19: 'IPMI_ERR_DRIVER_BUSY',
    20: 'IPMI_ERR_DRIVER_TIMEOUT',
    21: 'IPMI_ERR_MESSAGE_TIMEOUT',
    22: 'IPMI_ERR_COMMAND_INVALID_FOR_SELECTED_INTERFACE',
    23: 'IPMI_ERR_COMMAND_INVALID_OR_UNSUPPORTED',
    24: 'IPMI_ERR_BAD_COMPLETION_CODE',
    25: 'IPMI_ERR_BAD_RMCPPLUS_STATUS_CODE',
    26: 'IPMI_ERR_NOT_FOUND',
    27: 'IPMI_ERR_BMC_BUSY',
    28: 'IPMI_ERR_OUT_OF_MEMORY',
    29: 'IPMI_ERR_HOSTNAME_INVALID',
    30: 'IPMI_ERR_PARAMETERS',
    31: 'IPMI_ERR_DRIVER_PATH_REQUIRED',
    32: 'IPMI_ERR_IPMI_ERROR',
    33: 'IPMI_ERR_SYSTEM_ERROR',
    34: 'IPMI_ERR_INTERNAL_ERROR',
    35: 'IPMI_ERR_ERRNUMRANGE'
}


def _err(ctx):
    raise RuntimeError('IPMI error: {} ({})'.format(lib.ipmi_ctx_errnum(ctx),
                       ffi.string(lib.ipmi_ctx_errormsg(ctx))))

def _ferr(obj):
    raise RuntimeError('FIID error: {} ({})'.format(lib.fiid_obj_errnum(obj),
                       ffi.string(lib.fiid_obj_errormsg(obj))))

class FIIDObject:
    """
    A freeipmi interface declaration object

    Used for manipulating packets
    """
    def __init__(self, template):
        """
        Parameters:
        template -- a fiid_template_t ffi object
        """
        self.obj = lib.fiid_obj_create(template)

    def get_int(self, prop: str):
        """
        Gets the value of an integer property

        Parameters
        prop -- property name to get
        """
        val = 0
        ptr = ffi.new('uint64_t *', val)
        err = lib.FIID_OBJ_GET(self.obj, prop.encode(), ptr)
        if err == -1:
            _ferr(self.obj)
        return val

    def get_data(self, prop: str) -> bytes:
        prop = prop.encode()
        data_len = lib.fiid_obj_field_len_bytes(self.obj, prop)
        if data_len < 0:
            _ferr(self.obj)
        data = ffi.new('char[]', data_len)
        err = lib.fiid_obj_get_data(self.obj, prop, data, data_len)
        if err < 0:
            _ferr(fiid_obj)

    def __del__(self):
        lib.fiid_obj_destroy(self.obj)


class SDRRecord:
    """
    A sensor data record retrieved from an IPMI server
    """
    def __init__(self, obj):
        """
        Parameters:
        obj -- FIIDObject of response from sdr get request
        """
        self.next_record_id = obj.get_int('next_record_id')
        self.data = obj.get_data('record_data')


class Connection:
    """
    An IPMI connection
    """
    def __init__(self, host, user, pw, kg=b'', priv_level=4, cipher=3,
                 sess_timeout=20000, retrans_timeout=1000):
        """
        Make a new connection over IPMI 2.0.

        Parameters:
        host -- Hostname to connect to
        user -- IPMI username to use
        pw -- IPMI password to use

        Keyword Parameters:
        kg -- IPMI K_g (if left blank, pw is used)
        priv_level -- Desired IPMI privilege level to auth to
        sess_timeout -- Presumably the session is killed when this elapses
        retrans_timeout -- Presumably give up retransmitting when this elapses
        """
        self.ctx = lib.ipmi_ctx_create()

        workaround_flags = 0
        flags = 0
        c_kg = ffi.new('unsigned char[]', kg)
        err = lib.ipmi_ctx_open_outofband_2_0(
            self.ctx,
            host.encode(),
            user.encode(),
            pw.encode(),
            c_kg,
            len(c_kg) - 1,
            priv_level,
            cipher,
            sess_timeout,
            retrans_timeout,
            workaround_flags,
            flags
        )
        if err:
            _err(self.ctx)

    def _reserve_sdr_repo(self):
        """
        Take a reservation on the SDR repository
        """
        resp = FIIDObject(lib.tmpl_cmd_reserve_sdr_repository_rs)
        err = lib.ipmi_cmd_reserve_sdr_repository(self.ctx, resp.obj)
        if err == -1:
            _err(self.ctx)
        return resp.get_int('reservation_id')

    def _get_sdr_record(self, record: int, reservation: int = None):
        """
        Get a specific sensor record.

        Parameters:
        record -- desired record number to read, 0x0000 always exists

        Keyword parameters:
        reservation -- IPMI reservation id to use: get one
                       with _reserve_sdr_repo()
        """
        offset = 0x00  # offset into record, no idea why anyone would use this
        read = 0xff  # how much into the record it is desired to read

        if not reservation:
            reservation = self._reserve_sdr_repo()

        resp = FIIDObject(lib.tmpl_cmd_get_sdr_rs)
        err = lib.ipmi_cmd_get_sdr(
            self.ctx,
            reservation,
            record,
            offset,
            read,
            resp.obj
        )
        if err == -1:
            _err(self.ctx)
            return
        return SDRRecord(resp)

    def __del__(self):
        lib.ipmi_ctx_close(self.ctx)
        lib.ipmi_ctx_destroy(self.ctx)
