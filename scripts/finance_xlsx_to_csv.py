#!/usr/bin/env python3
"""Convert a finance workbook in XLSX format into the canonical CSV ledger."""

from __future__ import annotations

import argparse
import csv
import os
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS = {"main": MAIN_NS, "rel": REL_NS}


def column_index(cell_ref: str) -> int:
    value = 0
    for char in cell_ref:
        if not char.isalpha():
            break
        value = value * 26 + (ord(char.upper()) - 64)
    return value


def load_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    values: list[str] = []
    for si in root.findall("main:si", NS):
        parts: list[str] = []
        for element in si.iter():
            if element.tag == f"{{{MAIN_NS}}}t" and element.text:
                parts.append(element.text)
        values.append("".join(parts))
    return values


def load_sheet_targets(zf: zipfile.ZipFile) -> list[tuple[str, str]]:
    workbook = ET.fromstring(zf.read("xl/workbook.xml"))
    relationships = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    rel_map = {rel.attrib["Id"]: rel.attrib["Target"] for rel in relationships}
    targets: list[tuple[str, str]] = []
    for sheet in workbook.findall("main:sheets/main:sheet", NS):
        rel_id = sheet.attrib.get(f"{{{REL_NS}}}id", "")
        target = rel_map.get(rel_id, "")
        if not target:
            continue
        targets.append((sheet.attrib.get("name", "Sheet"), target))
    return targets


def read_cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "s":
        raw = cell.findtext("main:v", default="", namespaces=NS)
        if raw.isdigit():
            index = int(raw)
            if 0 <= index < len(shared_strings):
                return shared_strings[index]
        return raw
    if cell_type == "inlineStr":
        parts: list[str] = []
        for element in cell.iter():
            if element.tag == f"{{{MAIN_NS}}}t" and element.text:
                parts.append(element.text)
        return "".join(parts)
    raw = cell.findtext("main:v", default="", namespaces=NS)
    if raw:
        return raw
    raw = cell.findtext("main:is/main:t", default="", namespaces=NS)
    return raw


def read_sheet_rows(zf: zipfile.ZipFile, target: str, shared_strings: list[str]) -> list[list[str]]:
    sheet_path = target if target.startswith("xl/") else f"xl/{target}"
    sheet = ET.fromstring(zf.read(sheet_path))
    rows: list[list[str]] = []
    for row in sheet.findall("main:sheetData/main:row", NS):
        values: dict[int, str] = {}
        max_index = 0
        for cell in row.findall("main:c", NS):
            ref = cell.attrib.get("r", "")
            if not ref:
                continue
            index = column_index(ref)
            if index <= 0:
                continue
            max_index = max(max_index, index)
            values[index] = read_cell_value(cell, shared_strings)
        if max_index <= 0:
            continue
        ordered = [values.get(i, "") for i in range(1, max_index + 1)]
        rows.append(ordered)
    return rows


def convert_workbook(source: Path, destination: Path) -> dict[str, object]:
    source = source.expanduser().resolve(strict=False)
    destination = destination.expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(source) as zf:
        shared_strings = load_shared_strings(zf)
        sheets = load_sheet_targets(zf)
        if not sheets:
            raise ValueError("Workbook has no sheets")

        combined_rows: list[list[str]] = []
        header: list[str] | None = None

        for sheet_name, target in sheets:
            rows = read_sheet_rows(zf, target, shared_strings)
            if not rows:
                continue
            sheet_header = rows[0]
            if header is None:
                header = sheet_header
            for row in rows[1:]:
                combined_rows.append([sheet_name, *row])

    if header is None:
        header = []

    width = max((len(row) - 1 for row in combined_rows), default=0)
    if len(header) < width:
        header = header + [f"extra_{idx}" for idx in range(1, width - len(header) + 1)]
    elif len(header) > width:
        width = len(header)

    fd, temp_name = tempfile.mkstemp(prefix=destination.name + ".", suffix=".tmp", dir=str(destination.parent))
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        with temp_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(["sheet_name", *header])
            for row in combined_rows:
                sheet_name = row[0]
                values = row[1:]
                if len(values) < width:
                    values = values + [""] * (width - len(values))
                else:
                    values = values[:width]
                writer.writerow([sheet_name, *values])
        os.replace(temp_path, destination)
    finally:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)

    return {
        "source": str(source),
        "destination": str(destination),
        "sheetCount": len(sheets),
        "rowCount": len(combined_rows),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="XLSX workbook to convert.")
    parser.add_argument("destination", help="Canonical CSV ledger destination.")
    args = parser.parse_args(argv)

    result = convert_workbook(Path(args.source), Path(args.destination))
    print(result["destination"])
    print(result["rowCount"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
