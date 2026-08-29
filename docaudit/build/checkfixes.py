#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scan the assembled source for values CORRECTIONS.md forbids."""
import glob
import os
import re
import sys

# (id, regex, why) -- regexes run against normalised text (– and - unified)
FORBIDDEN = [
    ("A1",  r"1975[^.]{0,120}(cắt lớp vi tính|hình ảnh sẵn có)", "1975 NINDS definition had no imaging criterion"),
    ("A3",  r"(?<!phải )(?<!không )nguyên nhân hàng đầu gây tàn tật", "GBD 2021: 4th for DALYs, not leading cause of disability"),
    ("A5",  r"Wu[^.]{0,200}(12-15%|15-20%|25-30%)", "Wu reported 2d 3.5%, 30d 8.0%, 90d 9.2% only"),
    ("A6",  r"30-100 lần", "no source; matched cohorts give ~4-5x"),
    ("A8",  r"tử vong tim mạch khoảng 5%", "TIAregistry 5-year CV death was 2.7%"),
    ("A10", r"chuyển khám chuyên khoa thần kinh chậm 1-3 tuần", "EXPRESS median delay to assessment was 3 days"),
    ("A13", r"(Tiền sử TIA|tiền sử đột quỵ)[^.]{0,60}8-10 lần", "~4-5x, not 8-10x"),
    ("A14", r"5-10% người (trên|từ) 65", "USPSTF 0.5-1%; de Weerd 7.5% in men >=80"),
    ("A18", r"HYVET[^.]{0,150}(rõ rệt|có ý nghĩa)", "HYVET primary endpoint p=0.06, not significant"),
    ("A21", r"ASCEND[^.]{0,200}không giảm có ý nghĩa", "ASCEND was positive: RR 0.88, p=0.01"),
    ("A22", r"kính\s*-\s*mỡ[^.]{0,60}(dưới 300|300 µm)", "lipohyalinosis <200 um"),
    ("B1",  r"7 ngày khoảng 4,1%|7 ngày khoảng 8,1%", "those are the 2-day risks"),
    ("B5",  r"7-14 ngày", "ADC pseudonormalisation ~7-10 days"),
    ("B6",  r"rung nhĩ tiềm ẩn chiếm phần lớn", "occult AF explains a minority"),
    ("B15", r"CICAS[^.]{0,120}(châu Á|quần thể châu Á)", "CICAS was China-only"),
    ("B16", r"(đau nửa đầu|Đau nửa đầu)[^.]{0,120}một nửa", "migraine ~12-20% of mimics"),
    ("C1",  r"đạt đỉnh trong 7-30 ngày", "risk peaks in the first 48h-7 days"),
    ("C2",  r"[Aa]spirin[^.]{0,120}20-25% nguy cơ tái phát sớm", "Rothwell 2016: ~60% at 6 weeks"),
    ("C12", r"1,3% lên 1,7%", "SPARCL haemorrhagic stroke 1.4% -> 2.3%"),
    ("C13", r"tử vong do nguyên nhân mạch máu giảm có ý nghĩa", "SPARCL CV death p=0.11"),
    ("C18", r"[Ee]zetimibe[^|]{0,80}15-20%", "ezetimibe adds ~18-25%"),
    ("C19", r"dabigatran[^.]{0,80}giảm 35%", "RE-LY: 34% (RR 0.66)"),
    ("C23", r"NASCET, đo tỷ lệ giữa đường kính lòng mạch", "NASCET formula needs the complement"),
    ("C24", r"10-20 điểm phần trăm", "NASCET/ECST difference varies with degree"),
    ("C27", r"perindopril và indapamide[^.]{0,80}giảm 28%", "28% is the whole active arm; the combination gave 43%"),
    ("C29", r"[Mm]etformin[^.]{0,100}30 mL/phút", "start metformin at eGFR >=45"),
    ("C30", r"SGLT-2[^.]{0,160}(giảm nhồi máu não|giảm đột quỵ)", "SGLT-2 inhibitors do not reduce stroke"),
    ("C31", r"[Bb]ỏ thuốc lá[^.]{0,80}50% nguy cơ", "~29-34% relative reduction"),
    ("C32", r"trầm cảm[^.]{0,80}30-40%", "pooled ~31% (28-35)"),
    ("C36", r"HOPE-3[^.]{0,120}viên phối hợp|viên phối hợp[^.]{0,120}HOPE-3", "HOPE-3 is not a polypill trial"),
    ("C37", r"50-60% người bệnh duy trì", "unsourced; published rates are higher"),
    ("D2",  r"xảy ra ở 4,1% người bệnh", "RE-SPECT ESUS 4.1%/yr is an annualised rate"),
    ("D5",  r"CLOSE[^.]{0,120}trung vị 5,3", "CLOSE follow-up was a mean of 5.3 years"),
    ("D7",  r"RESPECT[^.]{0,120}trung bình 5,9", "RESPECT follow-up was a median of 5.9 years"),
    ("E-src", r"(?m)(^|[.!?]\s+)Nguồn\s*:", "captions must carry the citation inline, never a source line"),
    ("N1",  r"NOARTERY", "this trial does not exist"),
    ("N3",  r"8 biến cố chu thủ thuật", "CREST-2 8-vs-0 figure is unverifiable"),
    ("N8",  r"CYP2C19[^.]{0,200}30 ngày", "genotype-guided ticagrelor is 21 days (rec 4.8.15)"),
    ("F-x",  r"RESCUE-TIA", "name not present in reference 51"),
    ("F-par", r"\(Bảng [^)]+\)\s*\(Bảng", "stack cross-references into one parenthesis"),
]

# a hit is suppressed when the surrounding text is explicitly correcting the claim
NEGATION = re.compile(
    r"không phải|không làm giảm|không giảm|bị mô tả sai|thường bị nhầm|"
    r"trái với|ngược lại với|cần lưu ý rằng|thực chất|không đúng|"
    r"không được trình bày|không nên|khác với",
    re.I)

RESULTS_NOT_PUBLISHED = ["ENDOLOW", "LIBREXIA-STROKE", "Lp(a)HORIZON", "ORION-4",
                         "VICTORION-2P", "SAFER", "CLOSE-2"]


def normalise(s):
    return s.replace("–", "-").replace("—", "-").replace("−", "-")


def main(paths):
    files = []
    for p in paths:
        files.extend(sorted(glob.glob(p)) if any(c in p for c in "*?") else [p])
    total = 0
    for f in files:
        if not os.path.isfile(f):
            continue
        raw = normalise(open(f, encoding="utf-8").read())
        for cid, rx, why in FORBIDDEN:
            flags = re.I if cid != "E-src" else re.M
            for m in re.finditer(rx, raw, flags):
                window = raw[max(0, m.start() - 200):m.end() + 200]
                if NEGATION.search(window):
                    continue
                a = max(0, m.start() - 60)
                print("  ! [%s] %s" % (cid, os.path.basename(f)))
                print("      ...%s..." % raw[a:m.end() + 60].replace("\n", " "))
                print("      -> %s" % why)
                total += 1
        for name in RESULTS_NOT_PUBLISHED:
            for m in re.finditer(re.escape(name), raw):
                ctx = raw[max(0, m.start() - 180):m.end() + 180].replace("\n", " ")
                if not re.search(r"chưa (công bố|báo cáo|có kết quả)|đang tiến hành|chưa hoàn tất", ctx, re.I):
                    print("  ! [not-published] %s mentions %s without saying it has not reported"
                          % (os.path.basename(f), name))
                    print("      ...%s..." % ctx)
                    total += 1
    print("\nforbidden-value hits:", total)
    return total


if __name__ == "__main__":
    sys.exit(1 if main(sys.argv[1:]) else 0)
