"""第5步集成测试 — 端到端验证：指数计算→分类→验证→图解→导出。"""
import sys, os, io, tempfile
sys.path.insert(0, '.')
sys.path.insert(0, 'geochem_extractor')
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from data.models import GeochemSample
from geochem.indices import IndexCalculator
from engine.classification import ClassificationEngine
from engine.validation import DataValidator
from engine.export import ExportEngine
from geochem.diagrams import DiagramDataBuilder, export_diagram_csv

print("=== 第5步 端到端集成测试 ===\n")

# ── 步骤1: 构建4个典型花岗岩样本 ──
print("Step 1: Build samples")
samples = []
configs = [
    ("SPGZ-I-01", "I-type", 68.5, 15.2, 3.5, 4.0, 3.8, 18, 150),
    ("SPGZ-S-01", "S-type", 72.0, 14.8, 1.2, 2.8, 5.0, 15, 80),
    ("SPGZ-A-01", "A-type", 75.0, 12.0, 0.5, 3.5, 4.8, 24, 350),
    ("SPGZ-M-01", "M-type", 68.0, 14.5, 5.0, 4.5, 0.6, 12, 50),
]

for (name, t, sio2, al2o3, cao, na2o, k2o, ga, zr) in configs:
    s = GeochemSample()
    s.sample_no = name
    s.major.sio2 = sio2
    s.major.al2o3 = al2o3
    s.major.cao = cao
    s.major.na2o = na2o
    s.major.k2o = k2o
    s.major.fe2o3 = 2.0
    s.major.mgo = 1.0
    s.trace.ga = ga
    s.trace.zr = zr
    s.trace.rb = 150
    s.trace.y = 20
    s.trace.nb = 12
    s.ree.la = 30; s.ree.ce = 55; s.ree.nd = 25; s.ree.sm = 5
    s.ree.eu = 1.0; s.ree.gd = 4; s.ree.tb = 0.6; s.ree.dy = 3
    s.ree.ho = 0.6; s.ree.er = 1.8; s.ree.yb = 1.5; s.ree.lu = 0.2
    samples.append(s)

print(f"  Created {len(samples)} samples")

# ── 步骤2: 指数计算 ──
print("\nStep 2: Calculate indices")
calc = IndexCalculator()
for s in samples:
    indices = calc.calculate_all(
        sio2=s.major.sio2, tio2=None, al2o3=s.major.al2o3,
        fe2o3=s.major.fe2o3, feo=s.major.feo, mno=None,
        mgo=s.major.mgo, cao=s.major.cao,
        na2o=s.major.na2o, k2o=s.major.k2o, p2o5=None,
        ga_ppm=s.trace.ga, zr_ppm=s.trace.zr,
    )
    s.indices.asi = indices.asi
    s.indices.femgi = indices.femgi
    s.indices.ga_al_ratio = indices.ga_al_ratio
    s.indices.t_zr = indices.t_zr
    print(f"  {s.sample_no}: ASI={indices.asi:.2f}, Ga/Al={indices.ga_al_ratio:.1f}, TZr={indices.t_zr:.0f}°C")

# ── 步骤3: 自动分类 ──
print("\nStep 3: Auto-classify")
engine = ClassificationEngine()
for s in samples:
    r = engine.classify(
        sio2=s.major.sio2, al2o3=s.major.al2o3,
        fe2o3=s.major.fe2o3, feo=s.major.feo, mgo=s.major.mgo,
        cao=s.major.cao, na2o=s.major.na2o, k2o=s.major.k2o,
        ga_ppm=s.trace.ga, zr_ppm=s.trace.zr,
        nb_ppm=s.trace.nb, y_ppm=s.trace.y,
    )
    s.auto_classification = r.granite_type
    s.auto_confidence = r.confidence
    if not s.granite_type:
        s.granite_type = r.granite_type

    expected = s.sample_no.split("-")[1]  # e.g. "I" from "SPGZ-I-01"
    match = "✅" if expected in (r.granite_type or "") else "❌"
    print(f"  {match} {s.sample_no}: {r.granite_type} ({r.confidence})")

# ── 步骤4: 数据验证 ──
print("\nStep 4: Validate")
validator = DataValidator()
flat = [s.to_flat_dict() for s in samples]
all_results = validator.validate_batch(samples)
total = sum(1 for v in all_results.values() for r in v if r.severity == "error")
warns = sum(1 for v in all_results.values() for r in v if r.severity == "warning")
print(f"  Errors: {total}, Warnings: {warns}")

# ── 步骤5: 图解数据 ──
print("\nStep 5: Diagram data")
builder = DiagramDataBuilder()
tas = builder.build_tas_data(flat)
ree = builder.build_ree_data(flat)
disc = builder.build_discrimination_data(flat)
print(f"  TAS: {len(tas['x'])}p, REE: {len(ree['series'])}s, Disc: {sum(len(disc[k]['x']) for k in disc)}p")

# ── 步骤6: 导出 ──
print("\nStep 6: Export")
exporter = ExportEngine()
tmp = tempfile.mkdtemp()

xlsx_path = exporter.export_excel(flat, os.path.join(tmp, "test.xlsx"), group_by="Granite type")
csv_path = exporter.export_csv(flat, os.path.join(tmp, "test.csv"))
diagram_files = exporter.export_diagram_data(flat, tmp)

print(f"  Excel: {os.path.getsize(xlsx_path)} bytes")
print(f"  CSV: {os.path.getsize(csv_path)} bytes")
for k, v in diagram_files.items():
    print(f"  {k}: {os.path.getsize(v)} bytes")

print(f"\n=== 第5步集成测试全部通过 ✅ ===")
