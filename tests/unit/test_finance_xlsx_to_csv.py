from __future__ import annotations

import csv
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.finance_xlsx_to_csv import convert_workbook


def write_xlsx_fixture(path: Path) -> None:
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets>'
        '<sheet name="2024-Maio" sheetId="1" r:id="rId1"/>'
        '<sheet name="2024-Junho" sheetId="2" r:id="rId2"/>'
        '</sheets></workbook>'
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet2.xml"/>'
        '</Relationships>'
    )
    shared = [
        "Ano",
        "Mês",
        "Descrição",
        "Situação",
        "Valor",
        "Responsável",
        "2024",
        "4",
        "Taxa Junta Comercial",
        "Pago em 29/04/2024",
        "388.91",
        "Leandro/Roberto",
        "6",
        "Compra - Repetidor de Sinal Wifi",
        "Pago em 14/06/2024",
        "319.57",
    ]
    shared_xml = "".join(f"<si><t>{value}</t></si>" for value in shared)
    sheet1 = (
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetData>'
        '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c><c r="C1" t="s"><v>2</v></c><c r="D1" t="s"><v>3</v></c><c r="E1" t="s"><v>4</v></c><c r="F1" t="s"><v>5</v></c></row>'
        '<row r="2"><c r="A2" t="s"><v>6</v></c><c r="B2" t="s"><v>7</v></c><c r="C2" t="s"><v>8</v></c><c r="D2" t="s"><v>9</v></c><c r="E2" t="s"><v>10</v></c><c r="F2" t="s"><v>11</v></c></row>'
        '</sheetData></worksheet>'
    )
    sheet2 = (
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetData>'
        '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c><c r="C1" t="s"><v>2</v></c><c r="D1" t="s"><v>3</v></c><c r="E1" t="s"><v>4</v></c><c r="F1" t="s"><v>5</v></c></row>'
        '<row r="2"><c r="A2" t="s"><v>6</v></c><c r="B2" t="s"><v>12</v></c><c r="C2" t="s"><v>13</v></c><c r="D2" t="s"><v>14</v></c><c r="E2" t="s"><v>15</v></c><c r="F2" t="s"><v>11</v></c></row>'
        '</sheetData></worksheet>'
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
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
        zf.writestr("xl/sharedStrings.xml", f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="{len(shared)}" uniqueCount="{len(shared)}">{shared_xml}</sst>')
        zf.writestr("xl/worksheets/sheet1.xml", sheet1)
        zf.writestr("xl/worksheets/sheet2.xml", sheet2)


class FinanceXlsxToCsvTests(unittest.TestCase):
    def test_converts_workbook_to_combined_csv(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "Controle.xlsx"
            destination = root / "ledger.csv"
            write_xlsx_fixture(source)

            result = convert_workbook(source, destination)

            self.assertEqual(result["sheetCount"], 2)
            self.assertEqual(result["rowCount"], 2)
            self.assertTrue(destination.exists())

            with destination.open("r", encoding="utf-8", newline="") as fh:
                rows = list(csv.reader(fh))

            self.assertEqual(rows[0], ["sheet_name", "Ano", "Mês", "Descrição", "Situação", "Valor", "Responsável"])
            self.assertEqual(rows[1][0], "2024-Maio")
            self.assertEqual(rows[2][0], "2024-Junho")
            self.assertEqual(rows[2][3], "Compra - Repetidor de Sinal Wifi")


if __name__ == "__main__":
    unittest.main()
