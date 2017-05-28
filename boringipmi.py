from _freeipmi import ffi, lib


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
        """
        Get the value of a data property as bytes

        Parameters:
        prop -- property name to get
        """
        prop = prop.encode()
        data_len = lib.fiid_obj_field_len_bytes(self.obj, prop)
        if data_len < 0:
            _ferr(self.obj)
        data = ffi.new('char[]', data_len)
        err = lib.fiid_obj_get_data(self.obj, prop, data, data_len)
        if err < 0:
            _ferr(fiid_obj)
        return data

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
