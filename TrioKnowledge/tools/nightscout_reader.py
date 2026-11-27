"""Read-only Nightscout import. Credentials never appear in returned data or logs."""
import datetime as dt
import ipaddress
import json
import socket
import urllib.error
import urllib.parse
import urllib.request


class NightscoutError(ValueError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise NightscoutError('Nightscout redirected the request. Enter the final HTTPS site URL directly.')


def normalize_url(value):
    p = urllib.parse.urlsplit(value.strip())
    if p.scheme != 'https' or not p.hostname or p.username or p.password or p.query or p.fragment:
        raise NightscoutError('Use the HTTPS Nightscout site URL without credentials, query parameters or fragments.')
    try:
        addresses = socket.getaddrinfo(p.hostname, p.port or 443, type=socket.SOCK_STREAM)
    except OSError as error:
        raise NightscoutError('Nightscout hostname could not be resolved.') from error
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise NightscoutError('Use a public HTTPS Nightscout hostname; private/loopback destinations are not supported.')
    path = p.path.rstrip('/')
    if '/api/' in path:
        raise NightscoutError('Enter the Nightscout site root, not an API endpoint.')
    return urllib.parse.urlunsplit(('https', p.netloc, path, '', ''))


def read_json(url, headers=None):
    request = urllib.request.Request(url, headers={**(headers or {}), 'Accept': 'application/json'}, method='GET')
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        with opener.open(request, timeout=30) as response:
            raw = response.read(12 * 1024 * 1024 + 1)
        if len(raw) > 12 * 1024 * 1024:
            raise NightscoutError('Nightscout response is too large; select a shorter date range.')
        return json.loads(raw)
    except urllib.error.HTTPError as error:
        raise NightscoutError(f'Nightscout returned HTTP {error.code}. Check the site, token permissions and selected dates.') from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise NightscoutError('Could not read Nightscout securely. Check connectivity and the HTTPS certificate.') from None
    except (ValueError, UnicodeError):
        raise NightscoutError('Nightscout did not return valid JSON.') from None


def readonly_permissions(auth):
    groups = auth.get('permissionGroups')
    if not isinstance(groups, list) or not groups or any(not isinstance(group, list) for group in groups):
        raise NightscoutError('Nightscout did not expose verifiable token permissions; read-only access cannot be confirmed.')
    permissions = [p for group in groups for p in group]
    if not permissions:
        raise NightscoutError('The token grants no read permissions.')
    for permission in permissions:
        if not isinstance(permission, str):
            raise NightscoutError('Unrecognized Nightscout permission format.')
        parts = permission.split(':')
        if len(parts) != 3 or not set(parts[2].split(',')).issubset({'read', 'list'}):
            raise NightscoutError('This token has non-read permissions (possibly inherited from site defaults). Use an effectively read-only token.')
    return sorted(set(permissions))


def permits(permissions, collection):
    needed = ['api', collection, 'read']
    return any(all(part == '*' or value in part.split(',') for part, value in zip(permission.split(':'), needed)) for permission in permissions)


def iso(value):
    return dt.datetime.fromtimestamp(value / 1000, dt.timezone.utc).isoformat().replace('+00:00', 'Z')


def timestamp(record):
    value = record.get('date')
    if isinstance(value, (float, int)):
        return value
    for key in ('created_at', 'dateString', 'timestamp'):
        value = record.get(key)
        if isinstance(value, str):
            try:
                date = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
                if date.tzinfo is None:
                    date = date.replace(tzinfo=dt.timezone.utc)
                return date.timestamp() * 1000
            except ValueError:
                continue
    return None


def sanitize(value):
    import re
    if isinstance(value, list):
        return [sanitize(v) for v in value]
    if isinstance(value, dict):
        return {k: sanitize(v) for k, v in value.items() if not re.search(r'token|secret|password|credential|authorization|username|email|url', k, re.I)}
    if isinstance(value, str):
        return re.sub(r'https?://\S+', '[connection URL omitted]', value)
    return value


def summarize(data, start, end):
    grouped = {}
    invalid = duplicates = conflicts = 0
    for entry in data.get('entries', []):
        time = timestamp(entry)
        value = entry.get('sgv')
        if entry.get('type', 'sgv') != 'sgv' or not isinstance(value, (int, float)) or value <= 0 or time is None or not start <= time < end:
            invalid += 1
            continue
        if time in grouped:
            duplicates += 1
            if grouped[time] != value:
                grouped[time] = None
                conflicts += 1
        else:
            grouped[time] = value
    points = sorted((time, value) for time, value in grouped.items() if value is not None)
    duration = below = within = above = weighted = 0
    for i, (time, value) in enumerate(points):
        next_time = points[i + 1][0] if i + 1 < len(points) else end
        covered = max(0, min(5 * 60 * 1000, next_time - time, end - time))
        duration += covered
        weighted += covered * value
        if value < 70:
            below += covered
        elif value <= 180:
            within += covered
        else:
            above += covered
    treatments = data.get('treatments', [])
    in_range = [t for t in treatments if timestamp(t) is not None and start <= timestamp(t) < end]
    insulin = sum(t['insulin'] for t in in_range if isinstance(t.get('insulin'), (int, float)) and t['insulin'] > 0)
    carbs = sum(t['carbs'] for t in in_range if isinstance(t.get('carbs'), (int, float)) and t['carbs'] > 0)
    statuses = data.get('devicestatus', [])
    latest = max(statuses, key=lambda x: timestamp(x) or 0, default=None)
    enacted = sum(isinstance(s.get('openaps'), dict) and bool(s['openaps'].get('enacted')) for s in statuses)
    return {'start_utc': iso(start), 'end_utc': iso(end), 'glucose_samples': len(points),
            'coverage_percent': round(100 * duration / (end - start), 1),
            'time_weighted_mean_mgdl': round(weighted / duration, 1) if duration else None,
            'reference_bands_mgdl': {'below_70_percent': round(100 * below / duration, 1) if duration else None,
                                    '70_to_180_percent': round(100 * within / duration, 1) if duration else None,
                                    'above_180_percent': round(100 * above / duration, 1) if duration else None},
            'recorded_insulin_units': round(insulin, 3), 'recorded_carbs_grams': round(carbs, 1),
            'treatment_records': len(in_range), 'device_status_records': len(statuses),
            'status_records_with_enacted_data': enacted, 'latest_status': sanitize(latest),
            'excluded_glucose_records': invalid, 'duplicate_glucose_timestamps': duplicates,
            'conflicting_glucose_timestamps': conflicts,
            'limits': ['Glucose coverage is time-weighted with each reading covering at most five minutes. Uncovered time is excluded from band percentages.',
                       '70–180 mg/dL bands are descriptive reference bands, not an individualized target recommendation.',
                       'Recorded insulin may include logged external insulin and is not verified pump delivery. Suggested doses in device status are never counted as delivered insulin.',
                       'Saved presets and profiles do not establish which adjustments were active throughout the period. This summary does not establish cause or recommend dose changes.']}


def pull(url, token, start_iso, end_iso, reader=read_json, normalize=normalize_url, cancelled=lambda: False):
    base = normalize(url)
    if not isinstance(token, str) or not 8 <= len(token.strip()) <= 2048 or any(c.isspace() for c in token):
        raise NightscoutError('Enter a valid Nightscout read-only access token, not the API secret.')
    try:
        start_date = dt.datetime.fromisoformat(start_iso.replace('Z', '+00:00'))
        end_date = dt.datetime.fromisoformat(end_iso.replace('Z', '+00:00'))
        if start_date.tzinfo is None or end_date.tzinfo is None:
            raise ValueError()
        start, end = start_date.timestamp() * 1000, end_date.timestamp() * 1000
    except (ValueError, AttributeError):
        raise NightscoutError('Start and end must include a timezone.') from None
    if not 0 < end - start <= 14 * 86400000:
        raise NightscoutError('Choose an end after the start, covering at most 14 days.')
    auth = reader(base + '/api/v2/authorization/request/' + urllib.parse.quote(token.strip(), safe=''))
    permissions = readonly_permissions(auth)
    jwt = auth.get('token')
    if not isinstance(jwt, str) or not jwt:
        raise NightscoutError('Nightscout did not issue an authorization token.')
    headers = {'Authorization': 'Bearer ' + jwt}
    data, warnings, receipts = {}, [], []
    for collection in ('entries', 'treatments', 'devicestatus', 'profile'):
        if cancelled():
            raise NightscoutError('Nightscout import cancelled.')
        if not permits(permissions, collection):
            warnings.append(collection + ': token does not grant read permission; collection not fetched.')
            data[collection] = []
            continue
        data[collection] = []
        windows = [(start, end)] if collection == 'profile' else [(t, min(t + 86400000, end)) for t in range(int(start), int(end), 86400000)]
        try:
            for left, right in windows:
                if cancelled():
                    raise NightscoutError('Nightscout import cancelled.')
                query = {'count': '1000'}
                field = 'date' if collection == 'entries' else 'created_at'
                if collection != 'profile':
                    query[f'find[{field}][$gte]'] = str(int(left)) if field == 'date' else iso(left)
                query[f'find[{field}][$lt]'] = str(int(right)) if field == 'date' else iso(right)
                records = reader(base + '/api/v1/' + collection + '.json?' + urllib.parse.urlencode(query), headers)
                if not isinstance(records, list):
                    raise NightscoutError('Nightscout returned an unexpected collection format.')
                if len(records) >= 1000:
                    warnings.append(collection + ': a response reached the 1,000-record limit; this collection may be incomplete. Import a shorter range.')
                data[collection].extend(records)
                receipts.append({'collection': collection, 'method': 'GET', 'records': len(records), 'start_utc': iso(left), 'end_utc': iso(right)})
        except NightscoutError as error:
            warnings.append(collection + ': ' + str(error))
    sanitized = sanitize(data)
    return {'summary': summarize(sanitized, start, end), 'data': sanitized, 'permissions': permissions,
            'warnings': warnings, 'requests': receipts, 'read_only_verified': True,
            'scope': 'Date-bounded Nightscout history snapshot; no writes or remote commands are performed.'}
