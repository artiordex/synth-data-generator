"""Create reviewable Hangul examples without training a model or using real PII."""
from pathlib import Path
import pandas as pd
from synthetic_engine.common.types import ColumnPlan
from synthetic_engine.exporters.review_documents import build_review_documents


if __name__ == "__main__":
    frame = pd.DataFrame({"지역": ["서울", "부산", "대전"], "응답점수": [3, 4, 2], "이메일": ["sample@example.invalid", None, None]})
    plan = ColumnPlan(["지역"], ["응답점수"], ["이메일"], {"이메일": {"action": "drop"}}, {})
    directory = Path(__file__).resolve().parents[1] / "storage" / "outputs" / "review-example"
    files = build_review_documents(raw=frame, synthetic=frame.drop(columns="이메일"), plan=plan,
        original_filename="설문 예시.csv", model_type="예시 모형 (실제 학습 미수행)", metrics={},
        output_review_dir=directory, department_name="예시 부서", project_purpose="문서 양식 확인",
        metadata={"dataset_name": "심의자료 양식 예시", "special_notes": "양식 확인용 가상 데이터. 실제 측정결과 아님."})
    for path in files.values():
        print(path)
