#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Concatenate the section sources + reference list into one build source."""
import glob, json, os, re, sys

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src2')
ORDER = ['00_front', '10_datvande',
         '11_ch1_dinhnghia', '12_ch1_dichte', '13_ch1_cochebenh', '14_ch1_nguyco', '15_ch1_vaitro',
         '21_ch2_lamsang', '22_ch2_thangdiem', '23_ch2_hinhanh', '24_ch2_timmach',
         '25_ch2_phanloai', '26_ch2_phanbiet',
         '31_ch3_capcuu', '32_ch3_khangketap', '33_ch3_statin', '34_ch3_khangdong',
         '35_ch3_mach', '36_ch3_phongngua', '37_ch3_dacbiet',
         '41_ch4_esus', '42_ch4_pfo', '43_ch4_noiso', '44_ch4_tonghop',
         '50_ketluan']

def main(out_path, refs_json):
    parts, missing = [], []
    front = os.path.join(os.path.dirname(SRC), 'src', '00_front.txt')
    for name in ORDER:
        p = front if name == '00_front' else os.path.join(SRC, name + '.txt')
        if not os.path.exists(p):
            missing.append(name); continue
        txt = open(p, encoding='utf-8').read().strip('\n')
        # a chapter-opening H1 starts a new page; ĐẶT VẤN ĐỀ too
        txt = re.sub(r'^H1 (CHƯƠNG|ĐẶT VẤN ĐỀ|KẾT LUẬN|KIẾN NGHỊ)', r'H1P \1', txt, flags=re.M)
        parts.append(txt)
    refs = json.load(open(refs_json, encoding='utf-8'))
    parts.append('H1P TÀI LIỆU THAM KHẢO')
    parts.append('\n'.join('REF %s. %s' % (k, refs[k]) for k in sorted(refs, key=int)))
    open(out_path, 'w', encoding='utf-8').write('\n'.join(parts) + '\n')
    if missing:
        print('MISSING SECTIONS:', ', '.join(missing))
    print('sections written:', len(ORDER) - len(missing), 'of', len(ORDER))
    return missing

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'monograph_src.txt',
         sys.argv[2] if len(sys.argv) > 2 else '../refs_master.json')
