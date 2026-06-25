"""第2步集成测试 — 用5篇真实地质PDF验证提取准确率。"""
import sys, os
sys.path.insert(0, '.')
sys.path.insert(0, 'geochem_extractor')

import io, glob, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from services.batch_service import quick_process_pdf

test_pdfs = [p for p in glob.glob(r'C:\Users\XX\Desktop\花岗岩统计\spgz\*.pdf')[:5]]

total_tables = 0
success = 0
start = time.time()

for i, pdf_path in enumerate(test_pdfs):
    name = os.path.basename(pdf_path)
    result = quick_process_pdf(pdf_path)
    doc = result['pdf_doc']
    tables = result['tables']
    errors = result['errors']

    status = 'OK' if tables else 'EMPTY'
    elapsed = time.time() - start
    print(f"[{i+1}/5] {status} {name[:55]} -> {len(tables)} tables ({elapsed:.0f}s)")
    if tables:
        success += 1
        for j, t in enumerate(tables[:2]):
            print(f"  t{j+1}: {t.rows}r x {t.cols}c [{t.method}] conf={t.confidence:.2f}")
            if t.dataframe is not None:
                first_row = t.dataframe.iloc[0].tolist()[:5]
                print(f"  sample: {first_row}")
    if errors:
        print(f"  error: {str(errors[0])[:100]}")
    total_tables += len(tables)

total_time = time.time() - start
print(f"\n=== Summary ({total_time:.0f}s total) ===")
print(f"PDFs: {len(test_pdfs)}")
print(f"With tables: {success}/{len(test_pdfs)}")
print(f"Total tables: {total_tables}")
print(f"Avg: {total_tables/len(test_pdfs):.1f} tables/PDF")
