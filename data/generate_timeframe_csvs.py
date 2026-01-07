import json
from pathlib import Path
from datetime import datetime


DATA_DIR = Path(__file__).parent
FROM_DT = datetime(2020, 1, 1)
TO_DT = datetime(2025, 12, 31, 23, 59, 59)


def parse_datetime_from_parts(date_part, time_part=None):
    """Try multiple formats to parse datetime from date and optional time parts."""
    candidates = []
    if time_part:
        candidates.append(f"{date_part} {time_part}")
    else:
        candidates.append(date_part)

    # Try various formats
    fmts = [
        "%Y%m%d %H:%M:%S",
        "%Y%m%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y.%m.%d %H:%M:%S",
        "%Y.%m.%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y%m%d",
        "%Y-%m-%d",
        "%Y.%m.%d",
    ]

    for cand in candidates:
        for fmt in fmts:
            try:
                return datetime.strptime(cand, fmt)
            except Exception:
                continue

    # Last resort: try to extract digits
    try:
        digits = ''.join(ch for ch in date_part if ch.isdigit())
        if len(digits) >= 8:
            dt = datetime.strptime(digits[:8], "%Y%m%d")
            if time_part:
                # append time if possible
                tparts = [p for p in time_part.split(':') if p]
                h = int(tparts[0]) if len(tparts) > 0 else 0
                m = int(tparts[1]) if len(tparts) > 1 else 0
                s = int(tparts[2]) if len(tparts) > 2 else 0
                return datetime(dt.year, dt.month, dt.day, h, m, s)
            return dt
    except Exception:
        pass

    return None


def filter_csv_by_date(input_csv: Path, output_csv: Path):
    print(f"Processing CSV: {input_csv.name} -> {output_csv.name}")
    header = None
    written = 0

    with input_csv.open('r', encoding='utf-8', errors='replace') as fin:
        # read header
        header = fin.readline().strip()
        # ensure output folder exists
        with output_csv.open('w', encoding='utf-8', newline='') as fout:
            fout.write(header + '\n')

            for line in fin:
                parts = line.strip().split(',')
                if not parts or len(parts) < 6:
                    continue

                # Common formats:
                # 1) Date,Time,Open,High,Low,Close,Volume
                # 2) Datetime,Open,High,Low,Close,Volume
                dt = None
                if len(parts) >= 7:
                    date_part = parts[0]
                    time_part = parts[1]
                    dt = parse_datetime_from_parts(date_part, time_part)
                else:
                    # try first col as combined datetime
                    date_part = parts[0]
                    dt = parse_datetime_from_parts(date_part)

                if dt is None:
                    continue

                if FROM_DT <= dt <= TO_DT:
                    fout.write(line)
                    written += 1

    print(f"  Wrote {written:,} rows to {output_csv.name}")
    return written


def convert_jsonl_to_csv_filtered(jsonl_file: Path, csv_file: Path):
    print(f"Processing JSONL: {jsonl_file.name} -> {csv_file.name}")
    count = 0
    header = 'Date,Time,Open,High,Low,Close,Volume\n'
    with jsonl_file.open('r', encoding='utf-8', errors='replace') as fin, \
         csv_file.open('w', encoding='utf-8', newline='') as fout:
        fout.write(header)
        for line in fin:
            try:
                data = json.loads(line.strip())
            except Exception:
                continue

            # Expecting data['Date'] like 'YYYY.MM.DD HH:MM'
            dt_raw = data.get('Date') or data.get('datetime') or ''
            if not dt_raw:
                continue

            # Split
            if ' ' in dt_raw:
                date_part, time_part = dt_raw.split(' ', 1)
            else:
                date_part = dt_raw
                time_part = None

            dt = parse_datetime_from_parts(date_part, time_part)
            if dt is None:
                continue

            if not (FROM_DT <= dt <= TO_DT):
                continue

            # Normalize date/time format
            date_str = dt.strftime('%Y%m%d')
            time_str = dt.strftime('%H:%M:%S')

            row = f"{date_str},{time_str},{data.get('Open')},{data.get('High')},{data.get('Low')},{data.get('Close')},{data.get('Volume')}\n"
            fout.write(row)
            count += 1

    print(f"  Converted {count:,} rows to {csv_file.name}")
    return count


def main():
    # 1) Create 1m 2020-2025 from large 1m CSV if present
    candidates = [
        DATA_DIR / 'XAU_1m_2004-2025.csv',
        DATA_DIR / 'XAU_1m_converted.csv',
        DATA_DIR / 'xauusd_M1.csv',
    ]

    input_1m = None
    for c in candidates:
        if c.exists():
            input_1m = c
            break

    if input_1m is None:
        print('No 1m source CSV found. Skipping 1m creation.')
    else:
        out_1m = DATA_DIR / 'XAU_1m_2020-2025.csv'
        if out_1m.exists():
            print(f"{out_1m.name} already exists — skipping creation.")
        else:
            filter_csv_by_date(input_1m, out_1m)

    # 2) Convert JSONL timeframe files to filtered CSVs (skip 5m/3m if already present)
    timeframe_jsonl = {
        '15m': 'XAU_15m_data.jsonl',
        '30m': 'XAU_30m_data.jsonl',
        '1h': 'XAU_1h_data.jsonl',
        '4h': 'XAU_4h_data.jsonl',
        '5m': 'XAU_5m_data.jsonl'
    }

    for tf, fname in timeframe_jsonl.items():
        jsonl = DATA_DIR / fname
        out = DATA_DIR / f'XAU_{tf}_2020-2025.csv'
        # If 5m already has a 2020-2025 file, skip
        if tf == '5m':
            existing_alts = [DATA_DIR / 'XAUUSD_M5_2020-2025.csv', DATA_DIR / 'XAU_5m_2020-2025.csv']
            if any(p.exists() for p in existing_alts):
                print('5m 2020-2025 CSV already present — skipping 5m conversion')
                continue

        if not jsonl.exists():
            print(f"JSONL source for {tf} not found: {jsonl.name} — skipping")
            continue

        if out.exists():
            print(f"{out.name} already exists — skipping")
            continue

        convert_jsonl_to_csv_filtered(jsonl, out)


if __name__ == '__main__':
    main()
