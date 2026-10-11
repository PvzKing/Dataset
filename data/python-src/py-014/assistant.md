Two requirements shape the design: the file can be several GB, and some lines are broken.

- **Memory.** The script iterates over the file line by line and only keeps counters, so memory use stays flat no matter how large the log is. Rotated logs such as `access.log.2.gz` are read directly through `gzip`, and several files can be passed at once.
- **Malformed lines.** A line is counted only if it matches the combined format *and* its timestamp parses. Everything else is counted as malformed and skipped. That includes lines truncated by log rotation, timestamps like `13:99:00`, and binary junk that bots send to port 80. Invalid UTF-8 is replaced instead of raising `UnicodeDecodeError`.
- **Parsing.** A regex extracts the IP, timestamp, request, and status. It only relies on fields nginx always writes, so IPv6 addresses and odd user agents don't break it.
- **Hours keep their timezone offset.** Logs merged from servers in different zones would otherwise silently mix up hours.
- **Deterministic output.** Ties in the top-5 list are broken by IP address, so two runs over the same log print the same report.

```python
{{file logstats.py}}
```

Running it on a small sample log with three broken lines:

```
{{run python logstats.py access.log}}
```

For logs that are still being written, run it on a copy or a rotated file. A line that nginx is writing at that moment may be read half-finished, and it would then be counted as malformed.
