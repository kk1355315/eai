import tempfile
import unittest
from pathlib import Path

from openpyxl import load_workbook

from tools.export_foodkeeper_zh import (
    build_translated_workbook,
    flatten_sheet_rows,
    write_excel_xml,
    write_xlsx,
)


class ExportFoodkeeperZhTests(unittest.TestCase):
    def test_flatten_sheet_rows_preserves_column_order(self) -> None:
        sheet = {
            "name": "Product",
            "data": [
                [{"ID": 1.0}, {"Name": "Butter"}, {"Pantry_Metric": "Days"}],
                [{"ID": 2.0}, {"Name": "Milk"}, {"Pantry_Metric": None}],
            ],
        }

        rows = flatten_sheet_rows(sheet)

        self.assertEqual(
            rows,
            [
                {"ID": 1.0, "Name": "Butter", "Pantry_Metric": "Days"},
                {"ID": 2.0, "Name": "Milk", "Pantry_Metric": None},
            ],
        )

    def test_build_translated_workbook_translates_headers_and_values(self) -> None:
        workbook = {
            "fileName": "FMA-Data-v128.xlsx",
            "sheets": [
                {
                    "name": "Category",
                    "data": [[{"ID": 7.0}, {"Category_Name": "Produce"}, {"Subcategory_Name": None}]],
                },
                {
                    "name": "Product",
                    "data": [
                        [
                            {"ID": 1.0},
                            {"Category_ID": 7.0},
                            {"Name": "Butter"},
                            {"Name_subtitle": None},
                            {"Keywords": "Butter"},
                            {"Pantry_Metric": "Days"},
                            {"Pantry_tips": "Keep chilled after opening."},
                        ]
                    ],
                },
                {
                    "name": "Data Dictionary",
                    "data": [[{"Sheet": "Product"}, {"Column": "Pantry_Metric"}, {"Description": "Days, Weeks, Months"}]],
                },
            ],
        }
        translations = {
            "Produce": "农产品",
            "Butter": "黄油",
            "Keep chilled after opening.": "开封后继续冷藏。",
        }

        translated = build_translated_workbook(
            workbook,
            translator=lambda text: translations.get(text, text),
        )

        category_sheet = translated["sheets"][0]
        product_sheet = translated["sheets"][1]
        dictionary_sheet = translated["sheets"][2]

        self.assertEqual(category_sheet["name"], "分类")
        self.assertEqual(
            category_sheet["rows"][0],
            {"编号": 7.0, "分类名称": "农产品 | Produce", "子分类名称": None},
        )
        self.assertEqual(product_sheet["name"], "食品保质期")
        self.assertEqual(product_sheet["rows"][0]["名称"], "黄油 | Butter")
        self.assertEqual(product_sheet["rows"][0]["常温_单位"], "天")
        self.assertEqual(product_sheet["rows"][0]["常温_提示"], "开封后继续冷藏。 | Keep chilled after opening.")
        self.assertEqual(
            dictionary_sheet["rows"][0],
            {
                "工作表": "食品保质期 | Product",
                "字段": "常温_单位 | Pantry_Metric",
                "说明": "天, 周, 月",
            },
        )

    def test_write_excel_xml_outputs_excel_compatible_workbook(self) -> None:
        translated = {
            "sheets": [
                {
                    "name": "分类",
                    "rows": [
                        {"编号": 1.0, "分类名称": "农产品 | Produce"},
                        {"编号": 2.0, "分类名称": "乳制品 | Dairy"},
                    ],
                }
            ]
        }

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "foodkeeper_zh.xml"

            write_excel_xml(translated, output)

            xml_text = output.read_text(encoding="utf-8")
            self.assertIn('<?xml version="1.0"', xml_text)
            self.assertIn('Worksheet ss:Name="分类"', xml_text)
            self.assertIn("<Data ss:Type=\"String\">农产品 | Produce</Data>", xml_text)

    def test_write_xlsx_outputs_excel_workbook(self) -> None:
        translated = {
            "sheets": [
                {
                    "name": "分类",
                    "rows": [
                        {"编号": 1.0, "分类名称": "农产品 | Produce"},
                        {"编号": 2.0, "分类名称": "乳制品 | Dairy"},
                    ],
                }
            ]
        }

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "foodkeeper_zh.xlsx"

            write_xlsx(translated, output)

            workbook = load_workbook(output)
            sheet = workbook["分类"]
            self.assertEqual(sheet["A1"].value, "编号")
            self.assertEqual(sheet["B2"].value, "农产品 | Produce")


if __name__ == "__main__":
    unittest.main()
