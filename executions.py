import re
import urlparse
import itertools
from collections import namedtuple
from datetime import datetime

LogLine = namedtuple('LogLine', ['ip', 'timestamp', 'action', 'url',])
Execution = namedtuple('Execution', ['ip', 'timestamp', 'version_id'])


LOG_REGEX = re.compile(r"""^
                       (\d+(\.\d+){3})                                      #IP address
                       \s-\s-\s
                       \[(\d+/\w{3}/\d{4}:\d{2}:\d{2}:\d{2}\s[-+]\d{4})\]   #timestamp
                       \s"
                       (GET|POST|PUT|DELETE)                                #action
                       \s
                       ([^ "]+)                                             #url
                       """,
                       re.VERBOSE)


def find_conflicts(reader, start, delta):
    logs = parse(reader)
    filtered = filter_executions(logs, start)
    grouped = group_by_version(filtered)
    return filter_conflicts(grouped, delta)


def parse(reader):
    for line in reader:
        log = parse_line(line)
        if log:
            yield log


def parse_line(line):
    match = LOG_REGEX.match(line)
    if not match:
        return None

    ip = match.group(1)
    timestamp = parse_timestamp(match.group(3))
    action = match.group(4)
    url = match.group(5)

    return LogLine(ip=ip, timestamp=timestamp, action=action, url=url)


def parse_timestamp(text):
    text, _ = text.split(" ", 1)
    fmt = "%d/%b/%Y:%H:%M:%S"
    return datetime.strptime(text, fmt)


def filter_executions(logs, start):
    return (l for l in logs
            if all((l.timestamp >= start,
                    l.url.startswith('/lib/execute/execSetResults')))
            )


def group_by_version(logs):
    sorted_logs = sorted(fill_versions(logs),
                         key=lambda l: (l.version_id, l.ip))
    return itertools.groupby(sorted_logs, lambda l: l.version_id)


def fill_versions(logs):
    for log in logs:
        url = urlparse.urlparse(log.url)
        query = urlparse.parse_qs(url.query)
        yield Execution(ip=log.ip,
                        timestamp=log.timestamp,
                        version_id=query['version_id'][0])


def filter_conflicts(grouped_logs, delta):
    for version_id, version_logs in grouped_logs:
        grouped_ips = itertools.groupby(version_logs, lambda l: l.ip)
        latest_logs = tuple(max(ip_logs, key=lambda l: l.timestamp)
                            for _, ip_logs in grouped_ips)

        for left, right in zip(latest_logs[:-1], latest_logs[1:]):
            if left.timestamp + delta >= right.timestamp:
                yield (version_id, left, right)
