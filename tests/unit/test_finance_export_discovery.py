from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from scripts.finance_export_discovery import discover_finance_exports


def write_xlsx_fixture(path: Path, sheet_rows: list[list[str]], sheet_name: str = "Finance") -> None:
    shared_strings = []
    shared_index = {}

    def register(value: str) -> int:
        if value not in shared_index:
            shared_index[value] = len(shared_strings)
            shared_strings.append(value)
        return shared_index[value]

    rows_xml = []
    for row_num, row in enumerate(sheet_rows, start=1):
        cells = []
        for col_num, value in enumerate(row, start=1):
            ref = f"{chr(64 + col_num)}{row_num}"
            idx = register(value)
            cells.append(f'<c r="{ref}" t="s"><v>{idx}</v></c>')
        rows_xml.append(f'<row r="{row_num}">{"".join(cells)}</row>')

    shared_xml = "".join(f"<si><t>{value}</t></si>" for value in shared_strings)
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets><sheet name="{sheet_name}" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/></Relationships>'
    )
    sheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(rows_xml)}</sheetData></worksheet>'
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '</Types>'
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/></Relationships>'
    )
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", root_rels)
        zf.writestr("xl/workbook.xml", workbook)
        zf.writestr("xl/_rels/workbook.xml.rels", rels)
        zf.writestr("xl/sharedStrings.xml", f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="{len(shared_strings)}" uniqueCount="{len(shared_strings)}">{shared_xml}</sst>')
        zf.writestr("xl/worksheets/sheet1.xml", sheet)


class FinanceExportDiscoveryTestCase(unittest.TestCase):
    def test_discovers_supported_candidate_and_prefers_ledger_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            finance_dir = root / "reports" / "finance"
            finance_dir.mkdir(parents=True)
            ignored = finance_dir / "notes.md"
            ignored.write_text("not an export\n", encoding="utf-8")
            candidate = finance_dir / "monthly-ledger.csv"
            candidate.write_text("date,amount\n2026-04-05,100\n", encoding="utf-8")

            with mock.patch.dict(
                "os.environ",
                {"OPENCLAW_LEDGER_EXPORT_SEARCH_PATHS": str(root)},
                clear=False,
            ):
                report = discover_finance_exports(max_depth=4, limit=5)

        self.assertEqual(report["candidateCount"], 1)
        self.assertEqual(report["recommendedSource"]["path"], str(candidate))
        self.assertGreater(report["recommendedSource"]["score"], 0)
        self.assertIn("supported format .csv", report["recommendedSource"]["reasons"])

    def test_returns_empty_recommendation_when_no_candidate_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with mock.patch.dict(
                "os.environ",
                {"OPENCLAW_LEDGER_EXPORT_SEARCH_PATHS": str(root)},
                clear=False,
            ):
                report = discover_finance_exports(max_depth=2, limit=5)

        self.assertEqual(report["candidateCount"], 0)
        self.assertIsNone(report["recommendedSource"])

    def test_discovers_xlsx_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            finance_dir = root / "YukZ Tech" / "Financeiro"
            finance_dir.mkdir(parents=True)
            candidate = finance_dir / "Controle.xlsx"
            write_xlsx_fixture(
                candidate,
                [
                    ["Ano", "Mês", "Descrição", "Situação", "Valor", "Responsável"],
                    ["2024", "4", "Taxa Junta Comercial", "Pago em 29/04/2024", "388.91", "Leandro/Roberto"],
                ],
                sheet_name="2024-Maio",
            )

            with mock.patch.dict(
                "os.environ",
                {"OPENCLAW_LEDGER_EXPORT_SEARCH_PATHS": str(root)},
                clear=False,
            ):
                report = discover_finance_exports(max_depth=4, limit=5)

        self.assertEqual(report["candidateCount"], 1)
        self.assertEqual(report["recommendedSource"]["path"], str(candidate))
        self.assertIn("supported format .xlsx", report["recommendedSource"]["reasons"])


if __name__ == "__main__":
    unittest.main()
