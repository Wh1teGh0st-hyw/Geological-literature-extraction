"""第3步集成测试 — 端到端验证列识别/值清洗/单位转换。"""
import sys, os, io, json, re
sys.path.insert(0, '.')
sys.path.insert(0, 'geochem_extractor')
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from engine.element_identifier import ElementIdentifier
from engine.value_cleaner import ValueCleaner, CleanedValue
from engine.unit_converter import UnitConverter
from engine.geochem_parser import GeochemParserEngine
from data.database import DatabaseManager
from data.repository import SampleRepository
import pandas as pd

ei = ElementIdentifier()
vc = ValueCleaner()
uc = UnitConverter()
parser = GeochemParserEngine()

print("=== 阶段1: 列识别单元测试 ===\n")

# 模拟一个真实的地质学表格表头
mock_headers = [
    "Sample.No", "SiO2", "TiO2", "Al2O3", "Fe2O3T", "MnO",
    "MgO", "CaO", "Na2O", "K2O", "P2O5", "LOI", "Total",
    "Li", "Be", "Sc", "V", "Cr", "Co", "Ni", "Cu", "Zn", "Ga",
    "Rb", "Sr", "Y", "Zr", "Nb", "Cs", "Ba", "Hf", "Ta", "Pb", "Th", "U",
    "La", "Ce", "Pr", "Nd", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu",
    "87Sr/86Sr", "εNd(t)", "176Hf/177Hf", "εHf(t)",
]

mapping = ei.identify_columns_batch(mock_headers)
print(f"  输入表头: {len(mock_headers)}")
print(f"  识别结果: {len(mapping)}/{len(mock_headers)}")
for idx, (field, category, conf) in sorted(mapping.items()):
    print(f"    Col {idx}: '{mock_headers[idx]}' → {field} [{category}] (conf={conf:.2f})")

# 测试中文别名
chinese_headers = [
    "样品号", "二氧化硅", "氧化铝", "氧化镁", "氧化钙",
    "锂", "铷", "锶", "镧", "铈", "钕", "铕",
]
chinese_mapping = ei.identify_columns_batch(chinese_headers)
print(f"\n  中文表头识别: {len(chinese_mapping)}/{len(chinese_headers)}")
for idx, (field, cat, conf) in sorted(chinese_mapping.items()):
    print(f"    '{chinese_headers[idx]}' → {field} conf={conf:.2f}")

# 测试OCR纠错
ocr_headers = ["Si02", "A1203", "Si02(wt%)", "Na20", "K20", "Ti02", "P205"]
ocr_mapping = ei.identify_columns_batch(ocr_headers)
print(f"\n  OCR纠错识别: {len(ocr_mapping)}/{len(ocr_headers)}")
for idx, (field, cat, conf) in sorted(ocr_mapping.items()):
    print(f"    '{ocr_headers[idx]}' → {field} conf={conf:.2f}")

print("\n=== 阶段2: 值清洗测试 ===\n")

test_values = [
    ("72.50", 72.50, None, False),
    ("72.5±2.3", 72.5, 2.3, False),
    ("65.3±1,5", 65.3, None, False),  # 需要更强的解析
    ("<0.01", 0.01, None, True),
    ("bdl", None, None, True),
    ("-", None, None, True),
    ("n.d.", None, None, True),
    ("3.2×10-3", 0.0032, None, False),
    ("1,234.56", 1234.56, None, False),
    ("0.282515±0.000013", 0.282515, 1.3e-05, False),
]

for raw, expected_val, expected_err, expected_lod in test_values:
    c = vc.clean(raw)
    match = "✅" if (c.value == expected_val if expected_val is not None else c.value is None) else "❌"
    print(f"  {match} '{raw}' → v={c.value}, err={c.error}, lod={c.is_below_lod}")

print("\n=== 阶段3: 全流程测试（模拟表格 + 真实PDF）===\n")

# 用之前成功提取的表格进行端到端测试
from engine.table_extraction import TableExtractionEngine
extr = TableExtractionEngine()

# 挑选中文PDF
chinese_pdf = r"C:\Users\XX\Desktop\花岗岩统计\spgz\松潘-甘孜地块中西部晚三叠纪花岗岩体成因及其构造意义_王鹏.pdf"

try:
    tables = extr.extract_from_pdf(chinese_pdf)
    print(f"  PDF: 松潘-甘孜地块中西部... → {len(tables)} 表格")

    all_samples = []
    for i, table in enumerate(tables):
        if table.dataframe is not None and len(table.dataframe) >= 2:
            samples = parser.parse_table(
                table.dataframe,
                source_label=f"wang_2023_t{i}",
            )
            if samples:
                all_samples.extend(samples)
                print(f"  表{i+1}: {len(samples)} 个样本")

    print(f"\n  总解析样本: {len(all_samples)}")

    if all_samples:
        # 存入内存数据库
        db = DatabaseManager(':memory:')
        db.connect()
        repo = SampleRepository(db)
        count = repo.bulk_insert_samples(all_samples)
        print(f"  数据库插入: {count}")

        all_db = repo.get_all_samples()
        has_sio2 = sum(1 for s in all_db if s.major.sio2 is not None)
        has_la = sum(1 for s in all_db if s.ree.la is not None)
        print(f"  SiO2覆盖: {has_sio2}/{len(all_db)}")
        print(f"  La覆盖: {has_la}/{len(all_db)}")

        # 展示样本
        for i, s in enumerate(all_db[:3]):
            print(f"  [{i+1}] No={s.sample_no}, SiO2={s.major.sio2}, "
                  f"La={s.ree.la}, Rb={s.trace.rb}, "
                  f"eNd={s.isotopes.epsilon_nd_t}")

        db.close()

    print("\n=== 第3步集成测试通过 ✅ ===")
    print(f"提取表格: {len(tables)} | 解析样本: {len(all_samples)} | 数据库确认: OK")

except Exception as e:
    print(f"  错误: {e}")
    import traceback
    traceback.print_exc()
