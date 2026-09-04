import React, { useState } from 'react';
import { BookOpen, Shield, Cpu, Activity, FileCheck, X, Search, Sparkles } from 'lucide-react';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  isDarkMode?: boolean;
}

const DICTIONARY_SECTIONS = [
  {
    id: "dp",
    title: "차분 프라이버시 (Differential Privacy, DP)",
    icon: Shield,
    color: "text-emerald-500 dark:text-emerald-400",
    bgDark: "bg-emerald-950/40 border-emerald-800/40",
    bgLight: "bg-emerald-50/80 border-emerald-200",
    badge: "수학적 개인정보 보호",
    desc: "특정 개인의 데이터 포함 여부를 통계적으로 판별할 수 없도록 수학적 노이즈를 주입하는 기법입니다.",
    details: [
      { term: "프라이버시 예산 (Epsilon, ε)", text: "노이즈의 양을 조절하는 핵심 모수입니다. ε가 작을수록(예: 0.1~0.5) 프라이버시 보호 강도가 높아지고, ε가 클수록(예: 2.0~5.0) 원본 데이터 통계적 정확도가 높아집니다." },
      { term: "라플라스 메커니즘 (Laplace Mechanism)", text: "수치형 통계 집계량에 라플라스 분포 노이즈 Lap(Δf/ε)를 주입하여 개인정보 누출을 원천 방어합니다." },
      { term: "글로벌 민감도 (Sensitivity)", text: "단 한 명의 데이터 변경으로 인해 집계 결과가 변할 수 있는 최대 한계치입니다." }
    ]
  },
  {
    id: "anonymeter",
    title: "Anonymeter 3대 재식별 위험 평가 (EU GDPR 29조 기준)",
    icon: Activity,
    color: "text-amber-500 dark:text-amber-400",
    bgDark: "bg-amber-950/40 border-amber-800/40",
    bgLight: "bg-amber-50/80 border-amber-200",
    badge: "글로벌 공인 표준",
    desc: "EU GDPR Article 29 가이드라인에서 규정한 3대 익명화 취약성 공격 시뮬레이션입니다.",
    details: [
      { term: "1. 단일식별 위험 (Singling-Out Risk)", text: "합성데이터의 특정 레코드가 원본 데이터셋 내 단 1명의 고유한 개인을 고립·지목할 수 있는지 공격자가 추정하는 확률입니다." },
      { term: "2. 연결성 위험 (Linkability Risk)", text: "외부 보조 데이터셋(예: 주민등록, 건강보험, 신용정보)과 합성데이터의 다수 속성을 결합하여 동일인을 식별할 수 있는 위험도입니다." },
      { term: "3. 속성추론 위험 (Inference Risk)", text: "공격자가 대상의 일부 속성(나이, 직업 등)을 알고 있을 때, 민감한 비공개 속성(질병명, 소득 등)을 정확히 맞춰낼 확률입니다." }
    ]
  },
  {
    id: "models",
    title: "AI 합성 모델 아키텍처 (CTGAN / TVAE / Copula)",
    icon: Cpu,
    color: "text-sky-500 dark:text-cyan-400",
    bgDark: "bg-cyan-950/40 border-cyan-800/40",
    bgLight: "bg-sky-50/80 border-sky-200",
    badge: "딥러닝 & 통계 모델링",
    desc: "다양한 데이터 분포와 컬럼 간 상관관계를 보존하기 위한 첨단 생성 모델입니다.",
    details: [
      { term: "CTGAN (Conditional GAN)", text: "조건부 생성자(Generator)와 판별자(Discriminator)가 대립하며 학습하는 심층신경망 모델로, 불균형 범주형 변수와 다봉(multi-modal) 연속형 변수를 완벽히 모사합니다." },
      { term: "TVAE (Variational AutoEncoder)", text: "인코더와 디코더를 통해 데이터의 잠재 공간(Latent Space)을 학습하는 확률적 생성 모델로, 학습 안정성이 높고 중간 규모 정형데이터에 최적화되어 있습니다." },
      { term: "가우시안 코퓰라 (Gaussian Copula)", text: "주변분포와 결합분포를 분리하여 다변량 상관관계를 정밀하게 모델링하는 비모수/준모수 통계 기법으로, 고속 연산에 유리합니다." },
      { term: "터보 통계 샘플러 (Statistical Sampler)", text: "경량 비모수 다변량 확률 샘플링 엔진으로 1~3초 내에 초고속으로 대용량 데이터를 안전하게 생성합니다." }
    ]
  },
  {
    id: "jsd",
    title: "품질 평가 지표 (JSD / Wasserstein / 자동 평가 등급)",
    icon: Sparkles,
    color: "text-purple-500 dark:text-purple-400",
    bgDark: "bg-purple-950/40 border-purple-800/40",
    bgLight: "bg-purple-50/80 border-purple-200",
    badge: "통계적 유사도 검증",
    desc: "원본 데이터의 확률 분포가 합성데이터에 얼마나 정밀하게 유지되었는지를 정량화합니다.",
    details: [
      { term: "Jensen-Shannon 발산 (JSD, 0~1)", text: "KL 발산의 대칭적 확장형 지표로, 0에 가까울수록 원본과 합성데이터의 분포가 완전히 일치함을 의미합니다. (유사도 = 1 - JSD)" },
      { term: "종합 평가 등급 (S / A / B / C / F)", text: "품질 지수(70%)와 재식별 안전성 지수(30%)를 가중 결합하여 심의위원회 승인 통과 기준(80점 이상)을 자동 판정합니다." }
    ]
  },
  {
    id: "hwp",
    title: "심의위원회 3대 공문서 자동 바인딩",
    icon: FileCheck,
    color: "text-rose-500 dark:text-rose-400",
    bgDark: "bg-rose-950/40 border-rose-800/40",
    bgLight: "bg-rose-50/80 border-rose-200",
    badge: "행정 규제 컴플라이언스",
    desc: "공공기관 및 기업 데이터 심의위원회의 심의·승인을 위한 3종 법정 양식을 순수 파이썬 OLE2 엔진으로 무결하게 자동 생성합니다.",
    details: [
      { term: "1. 원본데이터 명세서", text: "데이터셋 명칭, 원본 행/열 수, 컬럼별 식별자/가명처리 분류, SHA-256 무결성 해시 기록" },
      { term: "2. 합성데이터 명세서", text: "적용 모델명, 학습 파라미터, 차분 프라이버시 설정, 생성 레코드 수 및 파일 무결성 해시" },
      { term: "3. 적정성 심의위원회 심의자료", text: "Anonymeter 3대 재식별 위험도 점수, JSD 품질 유사도, 가명·익명화 기법 적정성 종합 의견 자동 산출" }
    ]
  }
];

export const DataDictionaryModal: React.FC<Props> = ({ isOpen, onClose, isDarkMode = false }) => {
  const [searchTerm, setSearchTerm] = useState('');

  if (!isOpen) return null;

  const filteredSections = DICTIONARY_SECTIONS.filter(sec => 
    sec.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    sec.desc.toLowerCase().includes(searchTerm.toLowerCase()) ||
    sec.details.some(d => d.term.toLowerCase().includes(searchTerm.toLowerCase()) || d.text.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 dark:bg-black/80 backdrop-blur-sm p-4">
      <div className={`rounded-2xl w-full max-w-4xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden border ${
        isDarkMode ? 'bg-slate-900 border-slate-700 text-slate-100' : 'bg-white border-slate-200 text-slate-900'
      }`}>
        {/* Header */}
        <div className={`px-6 py-4 border-b flex items-center justify-between ${
          isDarkMode ? 'border-slate-800 bg-slate-900/90' : 'border-slate-200 bg-slate-50/80'
        }`}>
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
              isDarkMode ? 'bg-sky-500/20 border border-sky-500/40 text-sky-400' : 'bg-sky-100 border border-sky-200 text-sky-600'
            }`}>
              <BookOpen className="w-5 h-5" />
            </div>
            <div>
              <h2 className={`text-lg font-bold ${isDarkMode ? 'text-slate-100' : 'text-slate-900'}`}>
                데이터 & 합성데이터 지식 사전 (Data Dictionary)
              </h2>
              <p className={`text-xs ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                차분 프라이버시, Anonymeter 재식별 위험, AI 생성 모델, 심의 규정 총람
              </p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className={`p-2 rounded-lg transition-colors ${
              isDarkMode ? 'text-slate-400 hover:text-slate-100 hover:bg-slate-800' : 'text-slate-500 hover:text-slate-800 hover:bg-slate-200'
            }`}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Search */}
        <div className={`px-6 py-3 border-b ${
          isDarkMode ? 'border-slate-800 bg-slate-950/40' : 'border-slate-200 bg-slate-50/50'
        }`}>
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
            <input 
              type="text"
              placeholder="용어, 기법, 지표 검색 (예: 차분 프라이버시, Anonymeter, CTGAN, JSD, HWP...)"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className={`w-full pl-9 pr-4 py-2 border rounded-xl text-sm focus:outline-none focus:border-sky-500 transition-colors ${
                isDarkMode 
                  ? 'bg-slate-900 border-slate-700 text-slate-200 placeholder-slate-500' 
                  : 'bg-white border-slate-300 text-slate-900 placeholder-slate-400'
              }`}
            />
          </div>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1">
          {filteredSections.map((sec) => {
            const Icon = sec.icon;
            const bgClass = isDarkMode ? sec.bgDark : sec.bgLight;
            return (
              <div key={sec.id} className={`p-5 rounded-2xl border ${bgClass} space-y-4`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Icon className={`w-6 h-6 ${sec.color}`} />
                    <h3 className={`font-bold text-base ${isDarkMode ? 'text-slate-100' : 'text-slate-900'}`}>{sec.title}</h3>
                  </div>
                  <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${
                    isDarkMode ? 'bg-slate-800 border-slate-700 text-slate-300' : 'bg-white border-slate-300 text-slate-700 shadow-sm'
                  }`}>
                    {sec.badge}
                  </span>
                </div>
                <p className={`text-xs leading-relaxed ${isDarkMode ? 'text-slate-300' : 'text-slate-600'}`}>{sec.desc}</p>
                <div className={`space-y-2.5 pt-2 border-t ${isDarkMode ? 'border-slate-800/60' : 'border-slate-200'}`}>
                  {sec.details.map((item, idx) => (
                    <div key={idx} className={`rounded-xl p-3 border text-xs ${
                      isDarkMode ? 'bg-slate-900/80 border-slate-800' : 'bg-white border-slate-200 shadow-sm'
                    }`}>
                      <div className={`font-semibold mb-1 flex items-center gap-1.5 ${isDarkMode ? 'text-slate-200' : 'text-slate-900'}`}>
                        <span className="w-1.5 h-1.5 rounded-full bg-sky-500"></span>
                        {item.term}
                      </div>
                      <div className={`leading-relaxed ${isDarkMode ? 'text-slate-400' : 'text-slate-600'}`}>{item.text}</div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
          {filteredSections.length === 0 && (
            <div className={`text-center py-12 text-sm ${isDarkMode ? 'text-slate-500' : 'text-slate-400'}`}>
              검색어와 일치하는 사전 항목이 없습니다.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
