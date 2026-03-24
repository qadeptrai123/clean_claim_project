from __future__ import annotations

import json
from pathlib import Path


def split_into_4_equal_parts(input_path: Path) -> None:
    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("Input JSON must be a list of objects.")

    total = len(data)
    if total == 0:
        raise ValueError("Input list is empty, nothing to split.")

    # Chia thành 4 phần gần bằng nhau (chênh lệch tối đa 1 object)
    base = total // 4
    remainder = total % 4

    parts: list[list[dict]] = []
    start = 0
    for i in range(4):
        size = base + (1 if i < remainder else 0)
        part = data[start:start + size]
        parts.append(part)
        start += size

    # Đánh lại id toàn cục liên tục, không đứt quãng
    current_id = 1
    for part in parts:
        for obj in part:
            if isinstance(obj, dict):
                obj["id"] = current_id
                current_id += 1
            else:
                raise ValueError("Each item in input list must be an object (dict).")

    out_dir = input_path.parent
    for idx, part in enumerate(parts, start=1):
        out_file = out_dir / f"claims_formatted_part{idx}.json"
        with out_file.open("w", encoding="utf-8") as f:
            json.dump(part, f, ensure_ascii=False, indent=2)
        print(f"Wrote {len(part)} objects -> {out_file}")

    print(f"Done. Total objects: {total}, IDs reassigned from 1 to {total}.")


if __name__ == "__main__":
    input_file = Path(__file__).parent / "claims_formatted.json"
    split_into_4_equal_parts(input_file)
