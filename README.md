# boringipmi

An alpha IPMI library for python based on libfreeipmi

Since it appears that this is the only project on GitHub using libfreeipmi
(it's for the most part used internally by the command line utilities that
are part of freeipmi), please bear with us with compatibility. If your
IPMI device works with ipmi-sensors but not with boringipmi, that is a
*bug* and I'd like to fix it.

### System Requirements

* Python >=3.4 (Python 2 is unsupported; it may work, but it is 100% untested
  and is guarded against)
* A compiler
* libfreeipmi headers/libraries (freeipmi-devel on fedora)

### Example

```python
>>> import boringipmi
>>> conn = boringipmi.Connection('server1', 'user', 'password')
>>> with conn:
        print(conn.read_sdr_repo())
[<SDRRecordOEM #0 OEM 4156>,
 <SDRRecordFull #1 'VRM 1': sensor_num 1 'power_unit'>,
 <SDRRecordFull #2 'VRM 2': sensor_num 2 'power_unit'>,
 <SDRRecordFull #3 'UID Light': sensor_num 3 'oem_min'>,
 ...
 <SDRRecord #15 'entity_association_record'>,
 <SDRRecordFull #16 'Temp 1': sensor_num 14 'temperature'>,
 <SDRRecordFull #17 'Temp 2': sensor_num 15 'temperature'>,
 <SDRRecordFull #18 'Temp 3': sensor_num 16 'temperature'>,
 <SDRRecordFull #19 'Temp 4': sensor_num 17 'temperature'>
 ...
]
>>> with conn:
        print(conn.read_sensor('Temp 1'))
18
```

### Goal and rationale

Produce a high quality, simple to use, IPMI library which still permits
advanced usage.

This library is a wrapper over libfreeipmi, which is a very popular and mature
IPMI library (at least in its usage as ipmi-* utilities)

I also am not wrapping a command line utility, which improves performance and
completely sidesteps possible parsing bugs.

### How to gather information for a compatibility bug report

```bash
$ ipmi-sensors -h IPMI_HOST_HERE -D lanplus -u USERNAME -P --debug > bug 2>&1
```

I cannot guarantee that this 21k line long file contains no secrets,
however there is no obvious evidence of it doing so.

If you prefer to email it directly, my email is on my profile.
