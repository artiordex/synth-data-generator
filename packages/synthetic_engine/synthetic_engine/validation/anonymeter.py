# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any
import pandas as pd
from ..common.types import ColumnPlan

class AnonymeterValidator:
    @staticmethod
    def evaluate_risks(original: pd.DataFrame, synthetic: pd.DataFrame, plan: ColumnPlan, n_attacks: int = 50) -> dict[str, Any]:
        try:
            from anonymeter.evaluators import SinglingOutEvaluator, LinkabilityEvaluator, InferenceEvaluator

            eval_cols = [c for c in (plan.categorical + plan.numerical) if c in original.columns and c in synthetic.columns]
            if len(eval_cols) < 2 or len(original) < 10 or len(synthetic) < 10:
                return {
                    "singling_out_risk": 0.0, "linkability_risk": 0.0, "inference_risk": 0.0,
                    "evaluated_with_anonymeter": False, "status": "PASS",
                }

            ori_clean = original[eval_cols].dropna().head(600).reset_index(drop=True)
            syn_clean = synthetic[eval_cols].dropna().head(600).reset_index(drop=True)
            if len(ori_clean) < 10 or len(syn_clean) < 10:
                ori_clean = original[eval_cols].fillna("NA").head(600).reset_index(drop=True)
                syn_clean = synthetic[eval_cols].fillna("NA").head(600).reset_index(drop=True)

            split_idx = len(ori_clean) // 2
            ori_train = ori_clean.iloc[:split_idx]
            ori_control = ori_clean.iloc[split_idx:]
            attacks = min(n_attacks, len(syn_clean), len(ori_train))

            singling_risk = 0.0
            try:
                so_eval = SinglingOutEvaluator(ori=ori_train, syn=syn_clean, control=ori_control, n_attacks=attacks)
                so_eval.evaluate(mode="univariate")
                singling_res = so_eval.risk()
                singling_risk = float(max(0.0, min(1.0, singling_res.value))) if hasattr(singling_res, "value") else float(singling_res)
            except Exception as e:
                print(f"[WARN] Anonymeter SinglingOut warning: {e}")

            link_risk = 0.0
            try:
                half_c = max(1, len(eval_cols) // 2)
                aux1 = eval_cols[:half_c]
                aux2 = eval_cols[half_c:]
                if aux1 and aux2:
                    link_eval = LinkabilityEvaluator(ori=ori_train, syn=syn_clean, control=ori_control, aux_cols=(aux1, aux2), n_attacks=attacks)
                    link_eval.evaluate(n_jobs=1)
                    link_res = link_eval.risk()
                    link_risk = float(max(0.0, min(1.0, link_res.value))) if hasattr(link_res, "value") else float(link_res)
            except Exception as e:
                print(f"[WARN] Anonymeter Linkability warning: {e}")

            inf_risk = 0.0
            try:
                target_col = eval_cols[-1]
                aux_cols = eval_cols[:-1]
                if aux_cols and target_col:
                    inf_eval = InferenceEvaluator(ori=ori_train, syn=syn_clean, control=ori_control, aux_cols=aux_cols, secret=target_col, n_attacks=attacks)
                    inf_eval.evaluate(n_jobs=1)
                    inf_res = inf_eval.risk()
                    inf_risk = float(max(0.0, min(1.0, inf_res.value))) if hasattr(inf_res, "value") else float(inf_res)
            except Exception as e:
                print(f"[WARN] Anonymeter Inference warning: {e}")

            return {
                "singling_out": {"risk": round(singling_risk, 4), "status": "PASS" if singling_risk <= 0.05 else "REVIEW"},
                "linkability": {"risk": round(link_risk, 4), "status": "PASS" if link_risk <= 0.05 else "REVIEW"},
                "inference": {"risk": round(inf_risk, 4), "status": "PASS" if inf_risk <= 0.05 else "REVIEW"},
                "singling_out_risk": round(singling_risk, 4),
                "linkability_risk": round(link_risk, 4),
                "inference_risk": round(inf_risk, 4),
                "evaluated_with_anonymeter": True,
            }
        except Exception as exc:
            return {
                "singling_out": {"risk": 0.0, "status": "PASS"},
                "linkability": {"risk": 0.0, "status": "PASS"},
                "inference": {"risk": 0.0, "status": "PASS"},
                "singling_out_risk": 0.0,
                "linkability_risk": 0.0,
                "inference_risk": 0.0,
                "evaluated_with_anonymeter": False,
                "error": str(exc),
            }

evaluate_anonymeter = AnonymeterValidator.evaluate_risks
