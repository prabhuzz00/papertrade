"""Debug XTS quotes API for NIFTY options"""
import requests
import json
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from fetch_nifty_atm_options import NiftyATMOptionFetcher

f = NiftyATMOptionFetcher()
f.initialize()

inst_id = 48232  # 25900 CE
url = f"{f.base_url}/instruments/quotes"
headers = {"Content-Type": "application/json", "Authorization": f.token}

# Test 1: Current method (segment=2 integer)
print("=" * 60)
print(f"Testing instrument ID {inst_id} (25900 CE)")
print("=" * 60)

payload = {
    "instruments": [{"exchangeSegment": 2, "exchangeInstrumentID": inst_id}],
    "xtsMessageCode": 1502,
    "publishFormat": "JSON"
}
r = requests.post(url, json=payload, headers=headers, timeout=10, verify=False)
print(f"\nTest 1 - segment=2 (int), msgCode=1502:")
print(f"  Status: {r.status_code}")
data = r.json()
print(f"  Type: {data.get('type')}")
print(f"  Description: {data.get('description', 'N/A')}")
if 'result' in data and 'listQuotes' in data['result']:
    quotes = data['result']['listQuotes']
    print(f"  Quotes count: {len(quotes)}")
    if quotes:
        q = quotes[0]
        if isinstance(q, str):
            q = json.loads(q)
        tl = q.get('Touchline', {})
        print(f"  LTP: {tl.get('LastTradedPrice', 'MISSING')}")
        print(f"  Close: {tl.get('Close', 'MISSING')}")
        print(f"  Open: {tl.get('Open', 'MISSING')}")
else:
    print(f"  Full response: {r.text[:500]}")

# Test 2: Try with 1501 (full market data)
payload["xtsMessageCode"] = 1501
r2 = requests.post(url, json=payload, headers=headers, timeout=10, verify=False)
print(f"\nTest 2 - segment=2 (int), msgCode=1501:")
print(f"  Status: {r2.status_code}")
data2 = r2.json()
print(f"  Type: {data2.get('type')}")
if 'result' in data2 and 'listQuotes' in data2['result']:
    quotes2 = data2['result']['listQuotes']
    print(f"  Quotes count: {len(quotes2)}")
    if quotes2:
        q2 = quotes2[0]
        if isinstance(q2, str):
            q2 = json.loads(q2)
        tl2 = q2.get('Touchline', {})
        print(f"  LTP: {tl2.get('LastTradedPrice', 'MISSING')}")
        print(f"  Close: {tl2.get('Close', 'MISSING')}")
else:
    print(f"  Full response: {r2.text[:500]}")

# Test 3: Try a known working instrument (25950 CE = 48234)
print(f"\nTest 3 - Known working: 48234 (25950 CE), segment=2, msgCode=1502:")
payload3 = {
    "instruments": [{"exchangeSegment": 2, "exchangeInstrumentID": 48234}],
    "xtsMessageCode": 1502,
    "publishFormat": "JSON"
}
r3 = requests.post(url, json=payload3, headers=headers, timeout=10, verify=False)
data3 = r3.json()
if 'result' in data3 and 'listQuotes' in data3['result']:
    quotes3 = data3['result']['listQuotes']
    if quotes3:
        q3 = quotes3[0]
        if isinstance(q3, str):
            q3 = json.loads(q3)
        tl3 = q3.get('Touchline', {})
        print(f"  LTP: {tl3.get('LastTradedPrice', 'MISSING')}")
        print(f"  Close: {tl3.get('Close', 'MISSING')}")
else:
    print(f"  Full response: {r3.text[:500]}")

# Test 4: Try both instruments in a single request
print(f"\nTest 4 - Both instruments in single request:")
payload4 = {
    "instruments": [
        {"exchangeSegment": 2, "exchangeInstrumentID": 48232},
        {"exchangeSegment": 2, "exchangeInstrumentID": 48234}
    ],
    "xtsMessageCode": 1502,
    "publishFormat": "JSON"
}
r4 = requests.post(url, json=payload4, headers=headers, timeout=10, verify=False)
data4 = r4.json()
if 'result' in data4 and 'listQuotes' in data4['result']:
    quotes4 = data4['result']['listQuotes']
    print(f"  Quotes count: {len(quotes4)}")
    for i, q in enumerate(quotes4):
        if isinstance(q, str):
            q = json.loads(q)
        tl = q.get('Touchline', {})
        eid = q.get('ExchangeInstrumentID', 'unknown')
        print(f"  [{i}] InstID={eid}, LTP={tl.get('LastTradedPrice', 'MISSING')}, Close={tl.get('Close', 'MISSING')}")
else:
    print(f"  Full response: {r4.text[:500]}")

# Test 5: Verify instrument cache mapping
print(f"\nTest 5 - Instrument cache for nearby strikes:")
for strike in [25850, 25900, 25950, 26000]:
    for ot in ['CE', 'PE']:
        key = (strike, ot)
        if key in f.instrument_cache:
            info = f.instrument_cache[key]
            print(f"  {strike} {ot}: inst_id={info['instrument_id']}, display={info['display_name']}")
        else:
            print(f"  {strike} {ot}: NOT IN CACHE")
