import logging

from _freeipmi import ffi, lib


log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


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

    def have_prop(self, prop: str) -> bool:
        """
        Checks if a given property is available in the object

        Parameters:
        prop -- prop name to check for
        """
        ret = lib.fiid_obj_field_lookup(self.obj, prop.encode())
        if ret == -1:
            _ferr(self.obj)
        return bool(ret)

    def get_int(self, prop: str):
        """
        Gets the value of an integer property

        Parameters
        prop -- property name to get
        """
        ptr = ffi.new('uint64_t *')
        err = lib.FIID_OBJ_GET(self.obj, prop.encode(), ptr)
        if err == -1:
            _ferr(self.obj)
        return ptr[0]

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
        return ffi.unpack(data, data_len)

    def set_all_data(self, data):
        """
        Write data into the template so it can be accessed by field

        Parameters:
        data -- bytes of data to write
        """
        err = lib.fiid_obj_set_all(self.obj, data, len(data))
        if err < 0:
            _ferr(self.obj)

    def __del__(self):
        lib.fiid_obj_destroy(self.obj)


RECORD_TYPE = {
    0x01: 'full_sensor_record',
    0x02: 'compact_sensor_record',
    0x03: 'event_only_record',
    0x08: 'entity_association_record',
    0x09: 'device_relative_entity_association_record',
    0x10: 'generic_device_locator_record',
    0x11: 'fru_device_locator_record',
    0x12: 'management_controller_device_locator_record',
    0x13: 'management_controller_confirmation_record',
    0x14: 'bmc_message_channel_info_record',
    0xC0: 'oem_record',
}

SENSOR_TYPE = {
    0x00: 'reserved',
    0x01: 'temperature',
    0x02: 'voltage',
    0x03: 'current',
    0x04: 'fan',
    0x05: 'physical_security',
    0x06: 'platform_security_violation_attempt',
    0x07: 'processor',
    0x08: 'power_supply',
    0x09: 'power_unit',
    0x0A: 'cooling_device',
    0x0B: 'other_units_based_sensor',
    0x0C: 'memory',
    0x0D: 'drive_slot',
    0x0E: 'post_memory_resize',
    0x0F: 'system_firmware_progress',
    0x10: 'event_logging_disabled',
    0x11: 'watchdog1',
    0x12: 'system_event',
    0x13: 'critical_interrupt',
    0x14: 'button_switch',
    0x15: 'module_board',
    0x16: 'microcontroller_coprocessor',
    0x17: 'add_in_card',
    0x18: 'chassis',
    0x19: 'chip_set',
    0x1A: 'other_fru',
    0x1B: 'cable_interconnect',
    0x1C: 'terminator',
    0x1D: 'system_boot_initiated',
    0x1E: 'boot_error',
    0x1F: 'os_boot',
    0x20: 'os_critical_stop',
    0x21: 'slot_connector',
    0x22: 'system_acpi_power_state',
    0x23: 'watchdog2',
    0x24: 'platform_alert',
    0x25: 'entity_presence',
    0x26: 'monitor_asic_ic',
    0x27: 'lan',
    0x28: 'management_subsystem_health',
    0x29: 'battery',
    0x2A: 'session_audit',
    0x2B: 'version_change',
    0x2C: 'fru_state',
    0xC0: 'oem_min',
    0xFF: 'oem_max',
}


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
        self._data = obj.get_data('record_data')
        self._header = FIIDObject(lib.tmpl_sdr_record_header)
        self._header.set_all_data(self._data)
        self.record_id = self._header.get_int('record_id')
        self.record_type = RECORD_TYPE[self._header.get_int('record_type')]

    def __repr__(self):
        return '<{r.__class__.__name__} #{r.record_id} ' \
               '{r.record_type!r}>'.format(r=self)

    @staticmethod
    def create(obj):
        """
        Create the appropriate SDRRecord type for the given record

        Parameters:
        obj -- FIIDObject instance representing the raw record
        """
        data = obj.get_data('record_data')
        header = FIIDObject(lib.tmpl_sdr_record_header)
        header.set_all_data(data)
        desired_type = header.get_int('record_type')

        return (_record_types.get(desired_type, SDRRecord))(obj)


class SDRRecordCompact(SDRRecord):
    _template = lib.tmpl_sdr_compact_sensor_record
    _rtype = 'compact_sensor_record'

    def __init__(self, obj):
        SDRRecord.__init__(self, obj)
        assert self.record_type == self._rtype or \
               self.record_type == SDRRecordFull._rtype
        self._raw_templ = FIIDObject(self._template)
        self._raw_templ.set_all_data(self._data)

        self.sensor_number = self._raw_templ.get_int('sensor_number')
        self.sensor_type = SENSOR_TYPE[self._raw_templ.get_int('sensor_type')]

        self.name = ''
        if self._raw_templ.have_prop('id_string'):
            self.name = self._raw_templ.get_data('id_string').rstrip(b'\x00').decode('ascii')

    def __repr__(self):
        return '<{r.__class__.__name__} #{r.sensor_number} {r.name!r}: ' \
               '{r.sensor_type!r}>'.format(r=self)


class SDRRecordFull(SDRRecordCompact):
    _template = lib.tmpl_sdr_full_sensor_record
    _rtype = 'full_sensor_record'

    def __init__(self, obj):
        SDRRecordCompact.__init__(self, obj)
        assert self.record_type == self._rtype
        self._raw_templ = FIIDObject(self._template)
        self._raw_templ.set_all_data(self._data)


class SDRRecordOEM(SDRRecord):
    _template = lib.tmpl_sdr_oem_record
    _rtype = 'oem_record'

    def __init__(self, obj):
        SDRRecord.__init__(self, obj)
        assert self.record_type == self._rtype
        self._raw_templ = FIIDObject(self._template)
        self._raw_templ.set_all_data(self._data)

        self.oem_data = self._raw_templ.get_data('oem_data')
        self.manufacturer_id = self._raw_templ.get_int('manufacturer_id')

    def __repr__(self):
        return '<{r.__class__.__name__} #{r.record_id} OEM ' \
               '{r.manufacturer_id}>'.format(r=self)


_record_types = {
    0x1: SDRRecordFull,
    0x2: SDRRecordCompact,
    0xC0: SDRRecordOEM
}


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
        sess_timeout -- The session is killed after this number of ms
        retrans_timeout -- Presumably give up retransmitting when this elapses
        """
        self.ctx = lib.ipmi_ctx_create()

        workaround_flags = 0
        flags = 0
        c_kg = ffi.new('unsigned char[]', kg)
        self.conn_flags = (
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
        self._connect()

    def read_sdr_repo(self):
        """
        Read out the entire SDR repository and return it as SDRRecord
        objects
        """
        next_id = 0
        records = []

        while next_id != 0xffff:
            records.append(self._get_sdr_record(next_id))
            next_id = records[-1].next_record_id
        return records

    def _connect(self):
        lib.ipmi_ctx_close(self.ctx)
        err = lib.ipmi_ctx_open_outofband_2_0(*self.conn_flags)
        if err:
            self._err()

    def _reserve_sdr_repo(self):
        """
        Take a reservation on the SDR repository
        """
        resp = FIIDObject(lib.tmpl_cmd_reserve_sdr_repository_rs)
        self._check_retry(lib.ipmi_cmd_reserve_sdr_repository,
                          self.ctx, resp.obj)
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
        self._check_retry(
            lib.ipmi_cmd_get_sdr,
            self.ctx,
            reservation,
            record,
            offset,
            read,
            resp.obj
        )
        return SDRRecord.create(resp)

    def _err(self):
        """
        Call on detection of error condition
        Converts error number to exception or asks for retry
        """
        SESSION_TIMEOUT = 14
        ctx = self.ctx
        errnum = lib.ipmi_ctx_errnum(ctx)
        if errnum == SESSION_TIMEOUT:
            self._connect()
            return True
        raise RuntimeError('IPMI error: {} ({})'.format(errnum,
                           ffi.string(lib.ipmi_ctx_errormsg(ctx))))

    def _check_retry(self, func, *args):
        """
        Run the given function

        If it returns below zero, the actual error is checked and a retry
        may be attempted
        """
        retry_count = 0
        while retry_count < 2:
            retry_count += 1
            err = func(*args)
            # the joys of mutable state! What is actually happening is
            # self._err() either fixes the error condition or
            # throws an exception
            if err < 0:
                self._err()

    def __del__(self):
        lib.ipmi_ctx_close(self.ctx)
        lib.ipmi_ctx_destroy(self.ctx)
