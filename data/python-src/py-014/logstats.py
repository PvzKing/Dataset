"""Summarise an nginx access log in the default "combined" format.

Usage:
    python logstats.py access.log [access.log.1.gz ...]
"""
import gzip
import re
import sys
from collections import Counter
from datetime import datetime

# $remote_addr - $remote_user [$time_local] "$request" $status $body_bytes_sent "$http_referer" "$http_user_agent"
LINE = re.compile(r'(?P<ip>\S+) \S+ \S+ \[(?P<time>[^\]]+)\] "(?P<request>[^"]*)" (?P<status>\d{3}) \S+')


def open_log(path):
    # Logs can contain bytes that are not valid UTF-8 (scanners, TLS handshakes on port 80): never crash on them.
    opener = gzip.open if path.endswith(".gz") else open
    return opener(path, "rt", encoding="utf-8", errors="replace")


def summarise(paths):
    statuses, ips, per_hour, per_hour_5xx = Counter(), Counter(), Counter(), Counter()
    bad = 0
    for path in paths:
        with open_log(path) as lines:  # iterate line by line: memory stays flat for multi-GB files
            for line in lines:
                m = LINE.match(line)
                try:
                    when = datetime.strptime(m["time"], "%d/%b/%Y:%H:%M:%S %z") if m else None
                except ValueError:  # e.g. minute 99
                    when = None
                if when is None:
                    bad += 1
                    continue
                status, hour = m["status"], when.strftime("%Y-%m-%d %H:00 %z")
                statuses[status] += 1
                ips[m["ip"]] += 1
                per_hour[hour] += 1
                per_hour_5xx[hour] += status.startswith("5")
    return statuses, ips, per_hour, per_hour_5xx, bad


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    statuses, ips, per_hour, per_hour_5xx, bad = summarise(sys.argv[1:])
    total = sum(statuses.values())
    print(f"{total} requests parsed, {bad} malformed lines skipped")
    print("\nRequests per status:")
    for status, n in sorted(statuses.items()):
        print(f"  {status}  {n:>6}  {n / total:6.1%}")
    print("\nTop 5 client IPs:")
    for ip, n in sorted(ips.items(), key=lambda kv: (-kv[1], kv[0]))[:5]:
        print(f"  {ip:<16} {n:>6}")
    print("\n5xx share per hour:")
    for hour in sorted(per_hour):
        print(f"  {hour}  {per_hour_5xx[hour]:>4}/{per_hour[hour]:<5} {per_hour_5xx[hour] / per_hour[hour]:6.1%}")


if __name__ == "__main__":
    main()
