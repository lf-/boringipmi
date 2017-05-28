# boringipmi

This was going to be a neat project, but unfortunately there are some very big
issues with libfreeipmi that are breaking sensor readouts (which is basically
the only feature I need in an ipmi library).

Current progress:

```python
>>> conn = boringipmi.Connection('ipmihost', 'user', getpass.getpass())
>>> conn._get_sdr_record(0)
RuntimeError: IPMI error: 23 (b'command invalid or unsupported')
```

It isn't clear whether it's my IPMI device which is broken or freeipmi.

Regardless, I'm posting this here in case anyone wants to figure out what is
going on

Upon further investigation, it's likely that it is necessary to send a
reserve SDR repo request and pass the reservation ID.
