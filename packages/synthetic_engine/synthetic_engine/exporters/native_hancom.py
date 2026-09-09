"""Isolated native Hancom renderer/editor. No security-dialog bypass or reflow conversion."""
import json
import sys
from pathlib import Path


def run(spec):
    import pythoncom
    import win32com.client
    pythoncom.CoInitialize()
    hwp = None
    try:
        hwp = win32com.client.DispatchEx('HWPFrame.HwpObject')
        hwp.XHwpWindows.Item(0).Visible = False
        if not hwp.Open(str(Path(spec['source']).resolve()), '', ''):
            raise RuntimeError('한글 문서를 열지 못했습니다.')
        for item in spec.get('replacements', []):
            options = hwp.HParameterSet.HFindReplace
            hwp.HAction.GetDefault('AllReplace', options.HSet)
            options.Direction = hwp.FindDir('AllDoc')
            options.FindString = item['original']
            options.ReplaceString = item['replacement']
            options.ReplaceMode = 1
            options.IgnoreMessage = 1
            options.FindType = 1
            options.UseWildCards = 0
            hwp.HAction.Execute('AllReplace', options.HSet)
        if spec.get('output'):
            output = Path(spec['output']).resolve()
            if not hwp.SaveAs(str(output), output.suffix[1:].upper(), ''):
                raise RuntimeError('한글 원본 형식 저장에 실패했습니다.')
        if not hwp.SaveAs(str(Path(spec['pdf']).resolve()), 'PDF', ''):
            raise RuntimeError('한글 페이지 렌더링에 실패했습니다.')
    finally:
        if hwp is not None:
            hwp.Quit()
        pythoncom.CoUninitialize()


if __name__ == '__main__':
    run(json.loads(Path(sys.argv[1]).read_text(encoding='utf-8')))
# =============================================================================
# 파일명: native_hancom.py
# 경로: packages/synthetic_engine/synthetic_engine/exporters/native_hancom.py
# 목적: 한컴 네이티브 렌더링과 문서 편집을 실행함
# 작성자: 개발팀
# 작성일: 2026-09-09
# 수정일: 2026-09-09
# =============================================================================
