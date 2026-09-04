// FlowHunt 349종 AI·데이터 전문 용어집 + 플랫폼 합성데이터 핵심 용어 데이터셋
// Source: https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/

export interface GlossaryItem {
  id: string;
  name: string;
  description: string;
  url: string;
  category: '머신러닝 & 딥러닝' | '자연어 & 멀티모달' | 'LLM & 생성형 AI' | '보안 & 프라이버시' | '비즈니스 AI & 자동화' | 'AI 에이전트 & RAG';
  initial: string;
}

export const GLOSSARY_CATEGORIES = [
  '전체',
  '머신러닝 & 딥러닝',
  '자연어 & 멀티모달',
  'LLM & 생성형 AI',
  '보안 & 프라이버시',
  '비즈니스 AI & 자동화',
  'AI 에이전트 & RAG',
] as const;

export type GlossaryCategory = typeof GLOSSARY_CATEGORIES[number];

export const GLOSSARY_DATA: GlossaryItem[] = [
  {
    "id": "core-001",
    "name": "차분 프라이버시 (Differential Privacy, DP)",
    "description": "특정 개인의 데이터 포함 여부를 통계적으로 판별할 수 없도록 수학적 라플라스/가우시안 노이즈를 주입하는 기법으로, 프라이버시 예산(Epsilon, ε)을 통해 안전성과 유용성의 균형을 엄밀히 제어합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/",
    "category": "보안 & 프라이버시",
    "initial": "ㅊ"
  },
  {
    "id": "core-002",
    "name": "Anonymeter 3대 재식별 위험 평가",
    "description": "EU GDPR 제29조 기준 글로벌 공인 익명화 취약성 공격 시뮬레이션으로, 단일식별 위험(Singling-out), 연결성 위험(Linkability), 속성추론 위험(Inference)을 정량 평가합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/",
    "category": "보안 & 프라이버시",
    "initial": "A"
  },
  {
    "id": "core-003",
    "name": "CTGAN (Conditional WGAN-GP)",
    "description": "다양한 불균형 범주형 변수와 다봉(multi-modal) 연속형 수치 변수를 정밀하게 모사하기 위해 조건부 생성자와 Wasserstein 거리 기반 판별자가 대립 학습하는 정형 합성 신경망 모델입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/",
    "category": "LLM & 생성형 AI",
    "initial": "C"
  },
  {
    "id": "core-004",
    "name": "가우시안 코퓰라 (Gaussian Copula)",
    "description": "각 변수의 한계 분포(Marginal Distribution)와 다변량 상관관계를 분리하여 결합 누적 확률 분포를 고속으로 추정하는 통계적 합성 데이터 생성 알고리즘입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㄱ"
  },
  {
    "id": "core-005",
    "name": "Jensen-Shannon 발산 (JSD) 품질 유사도",
    "description": "원본 데이터와 합성 데이터의 확률 밀도 분포 간의 대칭적 거리를 측정(0~1)하는 지표로, 0에 가까울수록 두 분포가 완벽히 일치함을 뜻합니다 (분포 유사도 = 1.0 - JSD).",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/",
    "category": "머신러닝 & 딥러닝",
    "initial": "J"
  },
  {
    "id": "glossary-001",
    "name": "LarQL (LQL)",
    "description": "LarQL (LQL)은 LLM 가중치에 저장된 지식을 검사, 편집 및 감사하기 위한 SQL 유사 쿼리 언어입니다. 모델 내부를 쿼리하고 추론 경로를 추적하며 SEO의 의미적 근처를 발견하고 브랜드 인식을 감사하며 재교육 없이 대상 지식 패치를 적용합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/larql/",
    "category": "LLM & 생성형 AI",
    "initial": "L"
  },
  {
    "id": "glossary-002",
    "name": "AI 레드 티밍",
    "description": "AI 레드 티밍은 전문가들이 악의적인 공격자보다 먼저 취약점을 식별하기 위해 현실적인 공격 기법을 사용하여 AI 시스템(LLM 챗봇, 에이전트 및 파이프라인)을 체계적으로 조사하는 구조화된 적대적 보안 훈련입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/ai-red-teaming/",
    "category": "보안 & 프라이버시",
    "initial": "A"
  },
  {
    "id": "glossary-003",
    "name": "AI 챗봇 보안 감사",
    "description": "AI 챗봇 보안 감사는 AI 챗봇의 보안 상태에 대한 포괄적이고 체계적인 평가로, 프롬프트 인젝션, 탈옥, RAG 중독, 데이터 유출, API 남용을 포함한 LLM 특유의 취약점을 테스트하고 우선순위가 지정된 개선 보고서를 제공합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/ai-chatbot-security-audit/",
    "category": "보안 & 프라이버시",
    "initial": "A"
  },
  {
    "id": "glossary-004",
    "name": "AI 침투 테스트",
    "description": "AI 침투 테스트는 LLM 챗봇, 자율 에이전트, RAG 파이프라인을 포함한 AI 시스템의 구조화된 보안 평가로, 악의적인 공격자가 발견하기 전에 악용 가능한 취약점을 식별하기 위해 시뮬레이션 공격을 사용합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/ai-penetration-testing/",
    "category": "보안 & 프라이버시",
    "initial": "A"
  },
  {
    "id": "glossary-005",
    "name": "AI 탈옥",
    "description": "AI 탈옥은 대규모 언어 모델의 안전 가드레일과 행동 제약을 우회하는 기법을 의미하며, 유해한 콘텐츠, 정책 위반, 제한된 정보 공개를 포함하여 의도된 제한을 위반하는 출력을 생성하도록 만듭니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/jailbreaking-ai/",
    "category": "보안 & 프라이버시",
    "initial": "A"
  },
  {
    "id": "glossary-006",
    "name": "LLM 보안",
    "description": "LLM 보안은 프롬프트 인젝션, 탈옥, 데이터 유출, RAG 중독 및 모델 남용을 포함한 AI 특유의 위협으로부터 대규모 언어 모델 배포를 보호하는 데 사용되는 관행, 기술 및 통제를 포함합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/llm-security/",
    "category": "보안 & 프라이버시",
    "initial": "L"
  },
  {
    "id": "glossary-007",
    "name": "OWASP LLM Top 10",
    "description": "OWASP LLM Top 10은 대규모 언어 모델을 기반으로 구축된 애플리케이션의 가장 중요한 10가지 보안 및 안전 위험을 정리한 업계 표준 목록으로, 프롬프트 인젝션, 안전하지 않은 출력 처리, 학습 데이터 오염, 모델 서비스 거부 공격 및 6가지 추가 범주를 다룹니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/owasp-llm-top-10/",
    "category": "보안 & 프라이버시",
    "initial": "O"
  },
  {
    "id": "glossary-008",
    "name": "간접 프롬프트 인젝션",
    "description": "간접 프롬프트 인젝션은 AI 챗봇이 검색하고 처리하는 외부 콘텐츠(웹 페이지, 문서, 이메일 또는 데이터베이스 레코드 등)에 악의적인 명령어를 삽입하여, 사용자의 직접적인 개입 없이 챗봇이 공격자가 제어하는 명령어를 실행하도록 하는 공격입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/indirect-prompt-injection/",
    "category": "보안 & 프라이버시",
    "initial": "ㄱ"
  },
  {
    "id": "glossary-009",
    "name": "데이터 유출 (AI 컨텍스트)",
    "description": "AI 보안에서 데이터 유출은 AI 챗봇이 접근할 수 있는 민감한 데이터(PII, 자격 증명, 비즈니스 인텔리전스, API 키)를 공격자가 조작된 프롬프트, 간접 주입 또는 시스템 프롬프트 추출을 통해 추출하는 공격을 의미합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/data-exfiltration-ai/",
    "category": "보안 & 프라이버시",
    "initial": "ㄷ"
  },
  {
    "id": "glossary-010",
    "name": "시스템 프롬프트 추출",
    "description": "시스템 프롬프트 추출은 AI 챗봇을 속여 기밀 시스템 프롬프트의 내용을 공개하도록 만드는 공격으로, 개발자가 비공개로 유지하려고 했던 비즈니스 로직, 안전 지침, API 자격 증명 및 운영 세부 정보를 노출시킵니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/system-prompt-extraction/",
    "category": "보안 & 프라이버시",
    "initial": "ㅅ"
  },
  {
    "id": "glossary-011",
    "name": "적대적 머신러닝",
    "description": "적대적 머신러닝은 AI 모델 입력을 의도적으로 조작하여 잘못된 출력을 유발하는 공격과 이에 대한 방어를 연구합니다. 기술은 분류기를 속이는 감지할 수 없는 이미지 변조부터 LLM 동작을 탈취하는 교묘한 텍스트 프롬프트까지 다양합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/adversarial-ml/",
    "category": "보안 & 프라이버시",
    "initial": "ㅈ"
  },
  {
    "id": "glossary-012",
    "name": "컨텍스트 윈도우 조작",
    "description": "컨텍스트 윈도우 조작은 대규모 언어 모델의 유한한 컨텍스트 윈도우를 악용하는 공격을 의미하며, 컨텍스트 스터핑, 컨텍스트 오버플로우, 전략적 포이즈닝을 통해 성능을 저하시키거나 악성 페이로드를 숨기거나 이전 명령을 무효화합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/context-window-manipulation/",
    "category": "보안 & 프라이버시",
    "initial": "ㅋ"
  },
  {
    "id": "glossary-013",
    "name": "토큰 밀수",
    "description": "토큰 밀수는 사람이 텍스트를 읽는 방식과 LLM 토크나이저가 텍스트를 처리하는 방식 사이의 간극을 악용합니다. 공격자는 유니코드 변형, 너비가 없는 문자, 동형 이의 문자 또는 비정상적인 인코딩을 사용하여 콘텐츠 필터로부터 악의적인 명령을 숨기면서 토크나이저가 읽을 수 있도록 유지합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/token-smuggling/",
    "category": "보안 & 프라이버시",
    "initial": "ㅌ"
  },
  {
    "id": "glossary-014",
    "name": "프롬프트 유출",
    "description": "프롬프트 유출은 챗봇의 기밀 시스템 프롬프트가 모델 출력을 통해 의도치 않게 공개되는 것입니다. 이는 개발자가 비공개로 유지하려고 했던 운영 지침, 비즈니스 규칙, 안전 필터 및 구성 기밀 정보를 노출시킵니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/prompt-leaking/",
    "category": "보안 & 프라이버시",
    "initial": "ㅍ"
  },
  {
    "id": "glossary-015",
    "name": "llms.txt",
    "description": "llms.txt 파일은 대규모 언어 모델(LLM)이 웹사이트 콘텐츠에 접근하고 처리하는 방식을 최적화하기 위해 고안된 표준화된 마크다운 파일입니다. 웹사이트의 루트에 위치하여, AI 기반 상호작용을 향상시키기 위해 신중하게 선별된, 기계가 읽을 수 있는 인덱스를 제공합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/llms-txt/",
    "category": "LLM & 생성형 AI",
    "initial": "L"
  },
  {
    "id": "glossary-016",
    "name": "원격 MCP",
    "description": "원격 MCP(Model Context Protocol)는 AI 에이전트가 원격 서버에 호스팅된 표준화된 인터페이스를 통해 외부 도구, 데이터 소스 및 서비스에 접근할 수 있게 해주는 시스템입니다. 이를 통해 AI 모델은 학습 데이터 너머의 특화된 기능과 정보를 활용하여 보안과 유연성을 유지하면서 능력을 확장할 수 있습니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/remote-mcp/",
    "category": "보안 & 프라이버시",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-017",
    "name": "3D 재구성",
    "description": "3D 재구성에 대해 알아보세요: 이 첨단 프로세스가 실제 객체나 환경을 어떻게 포착하여 포토그래메트리, 레이저 스캐닝, AI 기반 알고리즘 등의 기술을 활용해 정교한 3D 모델로 변환하는지 살펴봅니다. 주요 개념, 활용 사례, 도전 과제, 미래 동향을 알아보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/3d-reconstruction/",
    "category": "자연어 & 멀티모달",
    "initial": "0-9"
  },
  {
    "id": "glossary-018",
    "name": "ABM 오케스트레이션",
    "description": "ABM 오케스트레이션은 마케팅과 영업을 정렬하여 고가치 계정을 맞춤형, 데이터 기반 캠페인으로 타겟팅하는 전략적 접근 방식입니다. 노력을 조율하고 분석을 활용함으로써, 조직은 전환 가능성이 높은 특정 계정과의 교류를 극대화하여 더 높은 ROI와 의미 있는 고객 관계를 이끌어냅니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/abm-orchestration/",
    "category": "AI 에이전트 & RAG",
    "initial": "A"
  },
  {
    "id": "glossary-019",
    "name": "AI SDR",
    "description": "AI SDR가 무엇인지, 인공지능 세일즈 개발 담당자가 어떻게 영업팀의 생산성과 효율성을 높이기 위해 잠재고객 발굴, 리드 자격 심사, 아웃리치, 팔로우업을 자동화하는지 알아보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/ai-sdr/",
    "category": "비즈니스 AI & 자동화",
    "initial": "A"
  },
  {
    "id": "glossary-020",
    "name": "AI 감독 기구",
    "description": "AI 감독 기구는 AI의 개발 및 배치를 모니터링, 평가, 규제하는 조직으로, 책임감 있고 윤리적이며 투명한 사용을 보장하고 차별, 프라이버시 침해, 책임 부재와 같은 위험을 완화합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/ai-oversight-bodies/",
    "category": "보안 & 프라이버시",
    "initial": "A"
  },
  {
    "id": "glossary-021",
    "name": "AI 검색",
    "description": "AI 검색은 검색 쿼리의 의도와 맥락적 의미를 이해하기 위해 머신러닝 모델을 사용하는 의미 기반 또는 벡터 기반 검색 방법론으로, 기존의 키워드 기반 검색보다 더 관련성 높고 정확한 결과를 제공합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/ai-search/",
    "category": "AI 에이전트 & RAG",
    "initial": "A"
  },
  {
    "id": "glossary-022",
    "name": "AI 규제 프레임워크",
    "description": "AI 규제 프레임워크는 인공지능 기술의 개발, 배포 및 사용을 관리하기 위해 고안된 구조화된 지침과 법적 조치입니다. 이러한 프레임워크는 AI 시스템이 윤리적이고 안전하며 사회적 가치에 부합하는 방식으로 작동하도록 보장하는 것을 목표로 합니다. 데이터 프라이버시, 투명성, 책임성, 위험 관리 등의 측면을 다루며, 책임 있는 AI 혁신을 촉진하는 동시에 잠재적 위험을 완화합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/ai-regulatory-frameworks/",
    "category": "보안 & 프라이버시",
    "initial": "A"
  },
  {
    "id": "glossary-023",
    "name": "AI 기반 경제적 영향",
    "description": "AI 기반 경제적 영향이란 인공지능이 생산성, 고용, 소득 분배, 경제 성장에 미치는 변화를 의미하며, 작업 자동화, 더 나은 의사 결정, 신시장 창출을 통해 나타납니다. 이러한 영향은 효율성 향상과 같은 긍정적인 측면과 일자리 대체, 불평등 심화와 같은 부정적인 측면을 모두 포함할 수 있습니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/ai-driven-economic-impact/",
    "category": "비즈니스 AI & 자동화",
    "initial": "A"
  },
  {
    "id": "glossary-024",
    "name": "AI 기반 마케팅",
    "description": "AI 기반 마케팅은 머신러닝, 자연어 처리(NLP), 예측 분석 등 인공지능 기술을 활용하여 업무를 자동화하고, 고객 인사이트를 얻으며, 개인화된 경험을 제공하고, 캠페인을 최적화하여 더 나은 결과를 이끌어냅니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/ai-powered-marketing/",
    "category": "자연어 & 멀티모달",
    "initial": "A"
  },
  {
    "id": "glossary-025",
    "name": "AI 기반 사기 탐지",
    "description": "AI를 활용한 사기 탐지는 머신러닝을 통해 실시간으로 사기 행위를 식별하고 완화합니다. 이는 은행, 전자상거래 등 다양한 산업에서 정확성, 확장성, 비용 효율성을 높이는 동시에 데이터 품질 및 규제 준수와 같은 과제를 해결합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/fraud-detection/",
    "category": "비즈니스 AI & 자동화",
    "initial": "A"
  },
  {
    "id": "glossary-026",
    "name": "AI 기반 스타트업",
    "description": "AI 기반 스타트업은 인공지능 기술을 중심으로 운영, 제품, 서비스를 혁신하고 자동화하며 경쟁 우위를 확보하는 비즈니스입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/ai-driven-startup/",
    "category": "비즈니스 AI & 자동화",
    "initial": "A"
  },
  {
    "id": "glossary-027",
    "name": "AI 기반 학생 피드백",
    "description": "AI 기반 학생 피드백은 인공지능을 활용하여 학생들에게 개인화된 실시간 평가 인사이트와 제안을 제공합니다. 머신러닝과 자연어처리(NLP)를 활용해 학습 결과를 향상시키고, 효율성을 높이며, 데이터 기반 인사이트를 제공하는 동시에 개인정보 보호와 공정성을 함께 고려합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/ai-based-student-feedback/",
    "category": "자연어 & 멀티모달",
    "initial": "A"
  },
  {
    "id": "glossary-028",
    "name": "AI 기술 트렌드",
    "description": "AI 기술 트렌드는 머신러닝, 대형 언어 모델, 멀티모달 AI, 생성형 AI 등 인공지능 분야의 현재와 미래를 이끄는 발전을 포함하며, 산업 전반에 영향을 미치고 미래 기술 개발을 주도합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/ai-technology-trend/",
    "category": "LLM & 생성형 AI",
    "initial": "A"
  },
  {
    "id": "glossary-029",
    "name": "AI 데이터 분석가",
    "description": "AI 데이터 분석가는 전통적인 데이터 분석 기술과 인공지능(AI), 머신러닝(ML)을 결합하여 인사이트를 도출하고, 트렌드를 예측하며, 다양한 산업 분야에서 의사결정을 개선합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/ai-data-analyst/",
    "category": "머신러닝 & 딥러닝",
    "initial": "A"
  },
  {
    "id": "glossary-030",
    "name": "AI 도입률",
    "description": "AI 도입률은 조직이 인공지능을 운영에 통합한 비율을 나타냅니다. 이 비율은 산업, 지역, 기업 규모에 따라 다르며, AI 기술의 다양한 활용과 영향을 반영합니다. 맥킨지의 2024년 조사에 따르면, AI 도입률은 72%로 급증했으며, 생성형 AI가 크게 기여했습니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/ai-adoption-rate/",
    "category": "LLM & 생성형 AI",
    "initial": "A"
  },
  {
    "id": "glossary-031",
    "name": "AI 모델 정확도와 AI 모델 안정성",
    "description": "머신러닝에서 AI 모델의 정확도와 안정성의 중요성을 알아보세요. 이러한 지표가 사기 탐지, 의료 진단, 챗봇과 같은 애플리케이션에 어떤 영향을 미치는지 배우고, 신뢰할 수 있는 AI 성능을 높이는 기법을 탐구해보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/ai-model-accuracy-and-ai-model-stability/",
    "category": "비즈니스 AI & 자동화",
    "initial": "A"
  },
  {
    "id": "glossary-032",
    "name": "AI 봇 차단",
    "description": "AI 봇 차단은 robots.txt를 활용해 AI 기반 봇의 웹사이트 데이터 접근을 방지하여, 무단 사용으로부터 콘텐츠를 보호합니다. 이는 콘텐츠 무결성, 프라이버시, 지적 재산권을 보호하며 SEO 및 법적 고려사항도 함께 생각합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/ai-bot-blocking/",
    "category": "보안 & 프라이버시",
    "initial": "A"
  },
  {
    "id": "glossary-033",
    "name": "AI 시스템 엔지니어",
    "description": "AI 시스템 엔지니어의 역할을 알아보세요: AI 시스템 설계, 개발, 유지보수, 머신러닝 통합, 인프라 관리, 비즈니스의 AI 자동화 주도.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/ai-systems-engineer/",
    "category": "비즈니스 AI & 자동화",
    "initial": "A"
  },
  {
    "id": "glossary-034",
    "name": "AI 시장 세분화",
    "description": "AI 시장 세분화는 인공지능을 활용하여 광범위한 시장을 공통된 특성에 따라 구체적인 세그먼트로 나누어, 기업이 고객 그룹을 개인화된 마케팅 전략으로 타겟팅할 수 있게 하여 효율성과 전환율을 높입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/ai-market-segmentation/",
    "category": "비즈니스 AI & 자동화",
    "initial": "A"
  },
  {
    "id": "glossary-035",
    "name": "AI 아트에서의 시드(Seed)",
    "description": "AI 아트에서 시드가 무엇인지, 이미지 생성 과정에 어떻게 영향을 미치는지, 그리고 아티스트들이 생성 예술 플랫폼에서 일관성 또는 창의적 탐구를 위해 시드를 어떻게 사용하는지 알아보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/seed-in-ai-art/",
    "category": "자연어 & 멀티모달",
    "initial": "A"
  },
  {
    "id": "glossary-036",
    "name": "AI 연구 보조금",
    "description": "AI 연구 보조금은 NSF, NEH 및 민간 기관과 같은 기관에서 인공지능 연구 프로젝트를 지원하기 위해 제공하는 재정적 지원입니다. 이러한 보조금은 새로운 AI 기술과 방법론의 개발을 지원하여 혁신을 촉진하고 근본적 및 응용 과제를 해결합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/ai-research-grants/",
    "category": "머신러닝 & 딥러닝",
    "initial": "A"
  },
  {
    "id": "glossary-037",
    "name": "AI 윤리",
    "description": "AI 윤리 가이드라인을 살펴보세요: AI 기술의 윤리적 개발, 배포 및 사용을 보장하는 원칙과 프레임워크를 안내합니다. 공정성, 투명성, 책임성, 글로벌 기준, 그리고 책임 있는 AI를 위한 전략에 대해 알아보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/ai-ethics/",
    "category": "머신러닝 & 딥러닝",
    "initial": "A"
  },
  {
    "id": "glossary-038",
    "name": "AI 인증 프로세스",
    "description": "AI 인증 프로세스는 인공지능 시스템이 사전에 정의된 기준과 규정을 충족하는지 평가하고 검증하는 포괄적인 절차입니다. 이러한 인증은 AI 기술의 신뢰성, 안전성, 윤리적 준수 여부를 평가하는 기준점 역할을 합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/ai-certification-processes/",
    "category": "보안 & 프라이버시",
    "initial": "A"
  },
  {
    "id": "glossary-039",
    "name": "AI 자동화 시스템",
    "description": "AI 자동화 시스템은 인공지능 기술과 자동화 프로세스를 통합하여, 학습, 추론, 문제 해결과 같은 인지 기능을 더해 기존 자동화의 한계를 넘어 복잡한 작업을 최소한의 인간 개입으로 수행할 수 있도록 합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/ai-automation-system/",
    "category": "비즈니스 AI & 자동화",
    "initial": "A"
  },
  {
    "id": "glossary-040",
    "name": "AI 컨설턴트",
    "description": "AI 컨설턴트는 AI 기술과 비즈니스 전략을 연결하여, 기업이 혁신, 효율성 및 성장을 이끌 수 있도록 AI 도입을 안내합니다. 그들의 역할, 책임, 필요한 역량, 그리고 AI 컨설팅이 비즈니스를 어떻게 변화시키는지 알아보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/ai-consultant/",
    "category": "비즈니스 AI & 자동화",
    "initial": "A"
  },
  {
    "id": "glossary-041",
    "name": "AI 콘텐츠 제작",
    "description": "AI 콘텐츠 제작은 인공지능을 활용하여 텍스트, 비주얼, 오디오 등 디지털 콘텐츠의 생성, 선별, 개인화를 자동화하고 향상시킵니다. 도구, 이점, 단계별 가이드를 통해 효율적이고 확장 가능한 콘텐츠 워크플로우를 알아보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/ai-content-creation/",
    "category": "AI 에이전트 & RAG",
    "initial": "A"
  },
  {
    "id": "glossary-042",
    "name": "AI 투명성",
    "description": "AI 투명성은 인공지능 시스템의 작동 방식과 의사결정 과정을 이해관계자에게 이해할 수 있도록 만드는 실천입니다. 그 중요성, 핵심 요소, 규제 프레임워크, 구현 기법, 과제, 그리고 실제 활용 사례를 알아보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/ai-transparency/",
    "category": "머신러닝 & 딥러닝",
    "initial": "A"
  },
  {
    "id": "glossary-043",
    "name": "AI 투자 동향",
    "description": "2024년 최신 AI 투자 동향을 살펴보세요. 투자 증가, 빅테크의 지배, 생성형 AI의 성장, 스타트업의 영향력 등 주요 흐름과 대형 거래, 산업별 투자, AI 투자 환경을 형성하는 도전 과제까지 확인할 수 있습니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/ai-funding-trends/",
    "category": "LLM & 생성형 AI",
    "initial": "A"
  },
  {
    "id": "glossary-044",
    "name": "AI 파트너십",
    "description": "대학교와 민간 기업 간의 AI 파트너십이 어떻게 학문적 지식과 산업적 응용을 결합하여 혁신, 연구, 그리고 역량 개발을 이끄는지 알아보세요. 성공적인 협업 사례, 주요 특징, 이점 및 도전과제에 대해 소개합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/ai-partnership/",
    "category": "머신러닝 & 딥러닝",
    "initial": "A"
  },
  {
    "id": "glossary-045",
    "name": "AI 품질 보증 전문가",
    "description": "AI 품질 보증 전문가는 테스트 계획을 개발하고, 테스트를 실행하며, 문제를 식별하고, 개발자와 협업하여 AI 시스템의 정확성, 신뢰성 및 성능을 보장합니다. 이 중요한 역할은 다양한 시나리오에서 AI 모델이 예상대로 작동하는지 테스트하고 검증하는 데 중점을 둡니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/ai-quality-assurance-specialist/",
    "category": "머신러닝 & 딥러닝",
    "initial": "A"
  },
  {
    "id": "glossary-046",
    "name": "AI 프로토타입 개발",
    "description": "AI 프로토타입 개발은 AI 시스템의 초기 버전을 설계하고 만드는 반복적인 과정으로, 본격적인 대량 생산 전에 실험, 검증, 자원 최적화를 가능하게 합니다. 주요 라이브러리, 접근 방식, 다양한 산업에서의 활용 사례를 알아보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/ai-prototype-development/",
    "category": "머신러닝 & 딥러닝",
    "initial": "A"
  },
  {
    "id": "glossary-047",
    "name": "AI와 인권",
    "description": "인공지능이 인권에 미치는 영향에 대해 탐구해 보세요. 서비스 접근성 향상과 같은 이점과 프라이버시 침해, 편향 등과 같은 위험 사이의 균형을 알아보세요. 국제적 기준, 규제적 과제, 그리고 기본권 보호를 위한 책임 있는 AI 도입의 중요성에 대해 학습할 수 있습니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/ai-and-human-rights/",
    "category": "보안 & 프라이버시",
    "initial": "A"
  },
  {
    "id": "glossary-048",
    "name": "AllenNLP",
    "description": "AllenNLP는 AI2에서 개발한 강력한 오픈소스 자연어 처리(NLP) 연구용 라이브러리로, PyTorch 기반으로 구축되었습니다. 모듈형 확장 도구, 사전 학습된 모델, spaCy 및 Hugging Face와 같은 라이브러리와의 손쉬운 통합을 제공하며, 텍스트 분류, 지시 대명사 해소 등 다양한 작업을 지원합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/allennlp/",
    "category": "자연어 & 멀티모달",
    "initial": "A"
  },
  {
    "id": "glossary-049",
    "name": "Amazon SageMaker",
    "description": "Amazon SageMaker는 AWS에서 제공하는 완전 관리형 기계 학습(ML) 서비스로, 데이터 과학자와 개발자가 통합 도구, 프레임워크, MLOps 기능을 활용해 손쉽게 기계 학습 모델을 신속하게 구축, 학습, 배포할 수 있도록 지원합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/amazon-sagemaker/",
    "category": "머신러닝 & 딥러닝",
    "initial": "A"
  },
  {
    "id": "glossary-050",
    "name": "B2B 데이터 보강",
    "description": "B2B 데이터 보강은 기업 간 데이터를 기업 특성, 기술 특성, 행동 인사이트 등으로 확장하여, 원시 데이터를 타깃 마케팅, 영업 개선, 전략적 의사결정을 위한 가치 있는 자원으로 탈바꿈시키는 과정입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/b2b-data-enrichment/",
    "category": "비즈니스 AI & 자동화",
    "initial": "B"
  },
  {
    "id": "glossary-051",
    "name": "BeenVerified",
    "description": "BeenVerified는 공개 기록과 소셜 미디어 데이터를 집계하여 개인 및 부동산에 대한 종합적인 배경 보고서를 제공하는 온라인 배경 조사 플랫폼입니다. 사람 찾기, 전화 및 이메일 역추적, 부동산 검색 서비스를 웹과 모바일 앱을 통해 제공합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/beenverified/",
    "category": "머신러닝 & 딥러닝",
    "initial": "B"
  },
  {
    "id": "glossary-052",
    "name": "BERT",
    "description": "BERT(양방향 인코더 표현 변환기)는 Google에서 개발한 오픈 소스 기계 학습 프레임워크로, 자연어 처리를 위한 혁신적인 기술입니다. BERT의 양방향 Transformer 아키텍처가 AI 언어 이해를 혁신한 방식과 NLP, 챗봇, 자동화 및 주요 연구 발전에 어떻게 활용되는지 알아보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/bert/",
    "category": "자연어 & 멀티모달",
    "initial": "B"
  },
  {
    "id": "glossary-053",
    "name": "BigML",
    "description": "BigML은 예측 모델의 생성 및 배포를 간소화하기 위해 설계된 머신러닝 플랫폼입니다. 2011년에 설립된 BigML의 미션은 머신러닝을 모든 사람이 접근하고 이해하며 저렴하게 활용할 수 있도록 하는 것으로, 사용자 친화적인 인터페이스와 강력한 자동화 도구를 제공해 머신러닝 워크플로우를 자동화합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/bigml/",
    "category": "AI 에이전트 & RAG",
    "initial": "B"
  },
  {
    "id": "glossary-054",
    "name": "BLEU 점수",
    "description": "BLEU 점수(Bilingual Evaluation Understudy)는 기계 번역 시스템이 생성한 텍스트의 품질을 평가하는 데 중요한 지표입니다. 2001년 IBM에서 개발된 이 지표는 번역 품질에 대한 인간 평가와 높은 상관관계를 보인 선구적인 척도였습니다. BLEU 점수는 자연어 처리(NLP) 분야에서 핵심적인 역할을 하며, 기계 번역 시스템 평가에 널리 사용되고 있습니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/bleu-score/",
    "category": "자연어 & 멀티모달",
    "initial": "B"
  },
  {
    "id": "glossary-055",
    "name": "BMXNet",
    "description": "BMXNet은 Apache MXNet을 기반으로 한 오픈 소스 바이너리 신경망(BNN) 구현체로, 바이너리 가중치와 활성화를 통해 저전력 기기에서 효율적인 AI 배포를 가능하게 합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/bmxnet/",
    "category": "머신러닝 & 딥러닝",
    "initial": "B"
  },
  {
    "id": "glossary-056",
    "name": "Botpress",
    "description": "Botpress에 대해 알아보고, 챗봇 구축을 위한 AI 플랫폼의 주요 기능, 장단점, 가격 옵션, 그리고 최적의 대화형 AI 솔루션 선택에 도움이 되는 대안들을 확인하세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/botpress/",
    "category": "비즈니스 AI & 자동화",
    "initial": "B"
  },
  {
    "id": "glossary-057",
    "name": "Caffe",
    "description": "Caffe는 BVLC에서 개발한 오픈 소스 딥러닝 프레임워크로, 컨볼루션 신경망(CNN) 구축에 최적화되어 속도와 모듈성에 강점을 지닙니다. 이미지 분류, 객체 탐지 등 다양한 AI 분야에서 널리 사용되며, 유연한 모델 구성, 빠른 처리 속도, 활발한 커뮤니티 지원을 제공합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/caffe/",
    "category": "자연어 & 멀티모달",
    "initial": "C"
  },
  {
    "id": "glossary-058",
    "name": "Chainer",
    "description": "Chainer는 유연하고 직관적이며 고성능의 신경망 플랫폼을 제공하는 오픈 소스 딥러닝 프레임워크로, 동적 define-by-run 그래프, GPU 가속, 다양한 아키텍처 지원을 특징으로 합니다. Preferred Networks에서 개발하였으며, 주요 기술 기업들의 기여가 이루어졌습니다. 연구, 프로토타이핑, 분산 학습에 이상적이나 현재는 유지보수 모드에 있습니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/chainer/",
    "category": "머신러닝 & 딥러닝",
    "initial": "C"
  },
  {
    "id": "glossary-059",
    "name": "Claude 3.5 소네트",
    "description": "Anthropic의 Claude 3.5 소네트에 대해 자세히 알아보세요: 다른 모델과의 비교, 강점과 약점, 추론, 코딩, 비주얼 작업 등 다양한 분야에서의 활용 사례를 확인할 수 있습니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/claude-3-5-sonnet/",
    "category": "머신러닝 & 딥러닝",
    "initial": "C"
  },
  {
    "id": "glossary-060",
    "name": "Clearbit",
    "description": "Clearbit는 특히 영업 및 마케팅 팀을 위한 강력한 데이터 활성화 플랫폼으로, 실시간 종합 B2B 데이터와 AI 기반 자동화를 활용하여 고객 데이터를 풍부하게 하고, 마케팅을 개인화하며, 영업 전략을 최적화할 수 있도록 지원합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/clearbit/",
    "category": "비즈니스 AI & 자동화",
    "initial": "C"
  },
  {
    "id": "glossary-061",
    "name": "Copilot",
    "description": "Microsoft Copilot은 Microsoft 365 앱 내에서 생산성과 효율성을 높여주는 AI 기반 어시스턴트입니다. OpenAI의 GPT-4를 기반으로 하며, 작업을 자동화하고 실시간 인사이트를 제공하며 Word, Excel, PowerPoint, Outlook, Teams와 같은 도구와 원활하게 통합됩니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/copilot/",
    "category": "LLM & 생성형 AI",
    "initial": "C"
  },
  {
    "id": "glossary-062",
    "name": "Copy.ai",
    "description": "Copy.ai는 OpenAI의 GPT-3를 기반으로 한 AI 글쓰기 도구로, 블로그, 이메일, 웹 카피 등 25개 이상의 언어로 고품질 콘텐츠를 생성하도록 설계되었습니다. 빠르고 효율적이며 사용하기 쉬운 AI 콘텐츠 생성이 필요한 마케터, 콘텐츠 제작자, 비즈니스에 이상적입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/copy-ai/",
    "category": "LLM & 생성형 AI",
    "initial": "C"
  },
  {
    "id": "glossary-063",
    "name": "Copysmith",
    "description": "Copysmith는 마케터, 콘텐츠 제작자, 기업이 효율적으로 고품질의 글 콘텐츠를 생성할 수 있도록 설계된 AI 기반 콘텐츠 제작 소프트웨어입니다. 인공지능을 활용해 블로그 포스트, 상품 설명, 소셜 미디어 콘텐츠, 이메일 등 다양한 유형의 콘텐츠를 빠르게 제작하여 콘텐츠 생성 프로세스를 간소화합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/copysmith/",
    "category": "머신러닝 & 딥러닝",
    "initial": "C"
  },
  {
    "id": "glossary-064",
    "name": "Crew AI",
    "description": "Crew AI에 대한 기본 정보를 알아보세요. 주요 기능, 장단점, 그리고 대안에 대한 빠른 개요를 제공합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/crew-ai/",
    "category": "머신러닝 & 딥러닝",
    "initial": "C"
  },
  {
    "id": "glossary-065",
    "name": "Did You Mean (DYM)",
    "description": "'Did You Mean'(DYM)은 자연어 처리(NLP)에서 사용자 입력의 오타나 철자 오류를 식별 및 교정하고, 대안을 제안하여 검색 엔진, 챗봇 등에서 사용자 경험을 향상시키는 기능입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/did-you-mean-dym/",
    "category": "자연어 & 멀티모달",
    "initial": "D"
  },
  {
    "id": "glossary-066",
    "name": "DL4J",
    "description": "DL4J(DeepLearning4J)는 자바 가상 머신(JVM)을 위한 오픈 소스 분산 딥러닝 라이브러리입니다. 이클립스 생태계의 일부로, 자바, 스칼라 및 기타 JVM 언어를 사용한 딥러닝 모델의 확장 가능한 개발 및 배포를 가능하게 합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/dl4j/",
    "category": "머신러닝 & 딥러닝",
    "initial": "D"
  },
  {
    "id": "glossary-067",
    "name": "F-점수 (F-측정치, F1 측정치)",
    "description": "F-점수(F-측정치, F1 점수)는 테스트나 모델의 정확도를 평가하는 통계적 지표로, 특히 이진 분류에서 사용됩니다. 정밀도와 재현율을 균형 있게 반영하여, 특히 불균형 데이터셋에서 모델 성능을 종합적으로 보여줍니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/f1-score/",
    "category": "머신러닝 & 딥러닝",
    "initial": "F"
  },
  {
    "id": "glossary-068",
    "name": "Fastai란 무엇인가?",
    "description": "Fastai는 PyTorch 위에서 구축된 딥러닝 라이브러리로, 고수준 API, 전이 학습, 계층적 아키텍처를 제공하여 비전, 자연어 처리, 표 형식 데이터 등 다양한 분야에서 신경망 개발을 쉽게 만들어 줍니다. Jeremy Howard와 Rachel Thomas가 개발한 Fastai는 오픈 소스이자 커뮤니티 주도로 발전하고 있어, 최신 AI 기술을 모두가 쉽게 활용할 수 있도록 합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/what-is-fastai/",
    "category": "자연어 & 멀티모달",
    "initial": "F"
  },
  {
    "id": "glossary-069",
    "name": "Flesch 가독성 지수",
    "description": "Flesch 가독성 지수는 텍스트가 얼마나 이해하기 쉬운지 평가하는 가독성 공식입니다. 1940년대 Rudolf Flesch가 개발했으며, 문장 길이와 음절 수를 기반으로 점수를 부여하여 텍스트의 복잡성을 나타냅니다. 교육, 출판, AI 분야에서 콘텐츠를 쉽게 접근할 수 있도록 널리 사용됩니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/flesch-reading-ease/",
    "category": "자연어 & 멀티모달",
    "initial": "F"
  },
  {
    "id": "glossary-070",
    "name": "Flux AI 모델",
    "description": "Black Forest Labs의 Flux AI 모델은 고도화된 머신러닝 알고리즘을 활용하여 자연어 프롬프트를 매우 정교하고 사진처럼 사실적인 이미지로 변환하는 첨단 텍스트-이미지 생성 시스템입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/flux-ai-model/",
    "category": "LLM & 생성형 AI",
    "initial": "F"
  },
  {
    "id": "glossary-071",
    "name": "Gensim",
    "description": "Gensim은 자연어 처리(NLP)를 위한 인기 있는 오픈 소스 파이썬 라이브러리로, 비지도 주제 모델링, 문서 색인화, 유사도 검색에 특화되어 있습니다. 대용량 데이터셋을 효율적으로 처리하며, 의미 분석을 지원하고 텍스트 마이닝, 분류, 챗봇 등 연구 및 산업 현장에서 널리 사용됩니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/gensim/",
    "category": "자연어 & 멀티모달",
    "initial": "G"
  },
  {
    "id": "glossary-072",
    "name": "Go-To-Market (GTM)",
    "description": "Go-To-Market(GTM) 전략은 기업이 신제품이나 서비스를 시장에 소개하고 판매하기 위해 사용하는 종합적인 계획으로, 타깃 시장을 이해하고 마케팅 및 유통을 최적화하여 위험을 최소화합니다. AI를 통합하면 시장 조사, 고객 타겟팅, 콘텐츠 개발을 더욱 정교하게 할 수 있어 GTM 전략이 한층 강화됩니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/go-to-market-gtm/",
    "category": "보안 & 프라이버시",
    "initial": "G"
  },
  {
    "id": "glossary-073",
    "name": "Horovod",
    "description": "Horovod는 다수의 GPU 또는 머신에 걸쳐 효율적으로 확장할 수 있도록 설계된 강력한 오픈소스 분산 딥러닝 학습 프레임워크입니다. TensorFlow, Keras, PyTorch, MXNet을 지원하며, 머신러닝 모델 학습의 속도와 확장성을 최적화합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/horovod/",
    "category": "머신러닝 & 딥러닝",
    "initial": "H"
  },
  {
    "id": "glossary-074",
    "name": "Jasper.ai",
    "description": "Jasper.ai는 마케터와 콘텐츠 제작자를 위해 설계된 AI 기반 콘텐츠 생성 도구로, 고급 언어 모델을 활용하여 효율적으로 고품질의 글을 제작할 수 있도록 돕습니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/jasper-ai/",
    "category": "LLM & 생성형 AI",
    "initial": "J"
  },
  {
    "id": "glossary-075",
    "name": "K-최근접 이웃",
    "description": "k-최근접 이웃(KNN) 알고리즘은 분류 및 회귀 작업에 사용되는 비모수적, 지도 학습 알고리즘입니다. 'k'개의 가장 가까운 데이터 포인트를 찾아 거리 측정 및 다수결 투표를 활용하여 결과를 예측하며, 단순성과 다양한 적용 가능성으로 잘 알려져 있습니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/k-nearest-neighbors/",
    "category": "머신러닝 & 딥러닝",
    "initial": "K"
  },
  {
    "id": "glossary-076",
    "name": "K-평균 군집화",
    "description": "K-평균 군집화는 데이터 포인트와 해당 군집 중심점 간의 제곱 거리 합을 최소화하여 데이터셋을 미리 정의된 개수의 뚜렷하고 겹치지 않는 군집으로 분할하는 인기 있는 비지도 기계 학습 알고리즘입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/k-means-clustering/",
    "category": "머신러닝 & 딥러닝",
    "initial": "K"
  },
  {
    "id": "glossary-077",
    "name": "KNIME",
    "description": "KNIME(콘스탄츠 정보 마이너)는 시각적 워크플로우, 원활한 데이터 통합, 고급 분석, 자동화를 제공하는 강력한 오픈소스 데이터 분석 플랫폼입니다. 다양한 산업 분야에서 활용됩니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/knime/",
    "category": "AI 에이전트 & RAG",
    "initial": "K"
  },
  {
    "id": "glossary-078",
    "name": "LangChain",
    "description": "LangChain은 대형 언어 모델(LLM)이 적용된 애플리케이션 개발을 위한 오픈 소스 프레임워크로, OpenAI의 GPT-3.5와 GPT-4와 같은 강력한 LLM을 외부 데이터 소스와 연동해 고급 자연어 처리(NLP) 애플리케이션을 쉽게 구축할 수 있도록 지원합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/langchain/",
    "category": "LLM & 생성형 AI",
    "initial": "L"
  },
  {
    "id": "glossary-079",
    "name": "LangGraph",
    "description": "LangGraph는 대형 언어 모델(LLM)을 활용하여 상태를 관리하고 여러 액터가 참여하는 애플리케이션을 구축할 수 있는 고급 라이브러리입니다. LangChain Inc에서 개발했으며, LangChain에 순환 계산 기능을 추가해 복잡하고 에이전트와 유사한 동작 및 인간이 직접 개입하는 워크플로우를 구현할 수 있습니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/langgraph/",
    "category": "AI 에이전트 & RAG",
    "initial": "L"
  },
  {
    "id": "glossary-080",
    "name": "LazyGraphRAG",
    "description": "LazyGraphRAG는 그래프 이론과 자연어 처리를 결합하여 AI 기반 데이터 검색의 효율성과 비용을 혁신적으로 최적화하는 Retrieval-Augmented Generation(RAG)의 혁신적인 접근법입니다. 동적으로 고품질 쿼리 결과를 제공하여 효율성과 비용을 모두 절감합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/lazygraphrag/",
    "category": "AI 에이전트 & RAG",
    "initial": "L"
  },
  {
    "id": "glossary-081",
    "name": "LightGBM",
    "description": "LightGBM(라이트 그라디언트 부스팅 머신)은 마이크로소프트에서 개발한 고급 그라디언트 부스팅 프레임워크입니다. 분류, 순위 매김, 회귀와 같은 고성능 머신러닝 작업을 위해 설계되었으며, 대용량 데이터셋을 효율적으로 처리하면서도 최소한의 메모리로 높은 정확도를 제공합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/lightgbm/",
    "category": "머신러닝 & 딥러닝",
    "initial": "L"
  },
  {
    "id": "glossary-082",
    "name": "LIX 가독성 측정법",
    "description": "LIX 가독성 측정법에 대해 알아보세요. 이 공식은 문장의 길이와 긴 단어를 분석하여 텍스트의 복잡성을 평가하도록 개발되었습니다. 교육, 출판, 저널리즘, AI 등 다양한 분야에서의 활용 사례를 이해할 수 있습니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/lix-readability-measure/",
    "category": "자연어 & 멀티모달",
    "initial": "L"
  },
  {
    "id": "glossary-083",
    "name": "LLM 비용",
    "description": "GPT-3, GPT-4와 같은 대형 언어 모델(LLM)의 학습 및 배포에 관련된 비용(연산, 에너지, 하드웨어)을 알아보고, 이러한 비용을 관리 및 절감할 수 있는 전략을 살펴보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/cost-of-llm/",
    "category": "LLM & 생성형 AI",
    "initial": "L"
  },
  {
    "id": "glossary-084",
    "name": "MCP: 모델 컨텍스트 프로토콜",
    "description": "모델 컨텍스트 프로토콜(MCP)은 대형 언어 모델(LLM)이 외부 데이터 소스, 도구 및 기능에 안전하고 일관되게 접근할 수 있도록 해주는 오픈 스탠다드 인터페이스로, AI 시스템을 위한 'USB-C' 역할을 합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/mcp-model-context-protocol/",
    "category": "보안 & 프라이버시",
    "initial": "M"
  },
  {
    "id": "glossary-085",
    "name": "MLflow",
    "description": "MLflow는 기계 학습(ML) 라이프사이클을 간소화하고 관리하기 위해 설계된 오픈 소스 플랫폼입니다. 이 플랫폼은 실험 추적, 코드 패키징, 모델 관리, 협업을 위한 도구를 제공하여 ML 프로젝트에서 재현성, 배포, 라이프사이클 제어를 향상시킵니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/mlflow/",
    "category": "머신러닝 & 딥러닝",
    "initial": "M"
  },
  {
    "id": "glossary-086",
    "name": "MXNet",
    "description": "Apache MXNet는 효율적이고 유연한 딥 뉴럴 네트워크의 학습 및 배포를 위해 설계된 오픈소스 딥러닝 프레임워크입니다. 뛰어난 확장성, 하이브리드 프로그래밍 모델, 다양한 언어 지원으로 잘 알려져 있으며, MXNet은 연구자와 개발자가 첨단 AI 솔루션을 구축할 수 있도록 지원합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/mxnet/",
    "category": "머신러닝 & 딥러닝",
    "initial": "M"
  },
  {
    "id": "glossary-087",
    "name": "NLP를 활용한 문서 검색",
    "description": "NLP를 활용한 향상된 문서 검색은 고급 자연어 처리 기술을 문서 검색 시스템에 통합하여, 자연어 쿼리를 사용해 방대한 텍스트 데이터를 검색할 때 정확성, 관련성, 효율성을 높입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/document-search-with-nlp/",
    "category": "자연어 & 멀티모달",
    "initial": "N"
  },
  {
    "id": "glossary-088",
    "name": "NLTK",
    "description": "Natural Language Toolkit(NLTK)는 상징적 및 통계적 자연어 처리(NLP)를 위한 포괄적인 파이썬 라이브러리 및 프로그램 모음입니다. 학계와 산업계에서 널리 사용되며, 토큰화, 형태소 분석, 표제어 추출, 품사 태깅 등 다양한 도구를 제공합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/nltk/",
    "category": "LLM & 생성형 AI",
    "initial": "N"
  },
  {
    "id": "glossary-089",
    "name": "NumPy",
    "description": "NumPy는 효율적인 배열 연산과 수학 함수를 제공하는 오픈 소스 파이썬 라이브러리로, 수치 계산에 필수적입니다. 빠르고 대규모 데이터 처리를 가능하게 하여 과학적 컴퓨팅, 데이터 과학, 머신러닝 워크플로우의 기반이 됩니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/numpy/",
    "category": "AI 에이전트 & RAG",
    "initial": "N"
  },
  {
    "id": "glossary-090",
    "name": "OpenCV",
    "description": "OpenCV는 고급 오픈소스 컴퓨터 비전 및 머신러닝 라이브러리로, 이미지 처리, 객체 탐지, 실시간 애플리케이션을 위한 2,500개 이상의 알고리즘을 다양한 언어와 플랫폼에서 제공합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/opencv/",
    "category": "자연어 & 멀티모달",
    "initial": "O"
  },
  {
    "id": "glossary-091",
    "name": "Pathways 언어 모델(PaLM)",
    "description": "Pathways 언어 모델(PaLM)은 구글의 첨단 대형 언어 모델 패밀리로, 텍스트 생성, 추론, 코드 분석, 다국어 번역 등 다양한 용도에 맞게 설계되었습니다. Pathways 이니셔티브를 기반으로 구축된 PaLM은 뛰어난 성능, 확장성, 책임 있는 AI 실천을 자랑합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/pathways-language-model-palm/",
    "category": "LLM & 생성형 AI",
    "initial": "P"
  },
  {
    "id": "glossary-092",
    "name": "Q-러닝",
    "description": "Q-러닝은 인공지능(AI)과 머신러닝, 특히 강화학습에서 핵심적인 개념입니다. 에이전트가 보상이나 페널티를 통한 상호작용과 피드백을 통해 최적의 행동을 학습하도록 하여, 시간이 지남에 따라 의사결정을 개선할 수 있게 합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/q-learning/",
    "category": "AI 에이전트 & RAG",
    "initial": "Q"
  },
  {
    "id": "glossary-093",
    "name": "R&D에서의 AI 프로젝트 관리",
    "description": "R&D에서의 AI 프로젝트 관리는 인공지능(AI)과 머신러닝(ML) 기술을 전략적으로 적용하여 연구개발 프로젝트의 관리를 향상시키는 것을 의미합니다. 이 통합은 프로젝트 기획, 실행, 모니터링을 최적화하여 데이터 기반의 인사이트를 제공하고, 의사결정, 자원 배분, 효율성을 개선하는 데 목적이 있습니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/ai-project-management-in-rd/",
    "category": "머신러닝 & 딥러닝",
    "initial": "R"
  },
  {
    "id": "glossary-094",
    "name": "ROC 곡선",
    "description": "수신자 조작 특성(ROC) 곡선은 이진 분류기 시스템의 성능을 판별 임계값을 변화시키면서 평가하는 데 사용되는 그래프적 표현입니다. 제2차 세계대전 중 신호 탐지 이론에서 유래한 ROC 곡선은 현재 머신러닝, 의학, AI에서 모델 평가에 필수적으로 사용됩니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/roc-curve/",
    "category": "머신러닝 & 딥러닝",
    "initial": "R"
  },
  {
    "id": "glossary-095",
    "name": "ROUGE 점수",
    "description": "ROUGE 점수는 기계가 생성한 요약 및 번역의 품질을 인간 기준과 비교하여 평가하는 데 사용되는 일련의 지표입니다. NLP에서 널리 사용되며, ROUGE는 내용 중첩과 재현율을 측정하여 요약 및 번역 시스템의 평가를 돕습니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/rouge-score/",
    "category": "자연어 & 멀티모달",
    "initial": "R"
  },
  {
    "id": "glossary-096",
    "name": "Rytr",
    "description": "Rytr에 대한 기본 정보를 알아보세요. 주요 기능, 장단점, 대안에 대한 빠른 개요입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/rytr/",
    "category": "머신러닝 & 딥러닝",
    "initial": "R"
  },
  {
    "id": "glossary-097",
    "name": "SEO 점수",
    "description": "SEO 점수는 웹사이트가 SEO 모범 사례를 얼마나 잘 준수하는지를 수치로 나타낸 것으로, 기술적 요소, 콘텐츠 품질, 사용자 경험, 모바일 반응성을 평가합니다. SEO 점수를 이해하고 개선하는 것은 검색 엔진 결과에서 웹사이트의 가시성을 높이는 데 매우 중요합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/seo-score/",
    "category": "머신러닝 & 딥러닝",
    "initial": "S"
  },
  {
    "id": "glossary-098",
    "name": "spaCy",
    "description": "spaCy는 속도, 효율성, 그리고 토큰화, 품사 태깅, 개체명 인식과 같은 실전 사용에 적합한 기능들로 유명한, 고급 자연어 처리(NLP)를 위한 강력한 오픈 소스 파이썬 라이브러리입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/spacy/",
    "category": "LLM & 생성형 AI",
    "initial": "S"
  },
  {
    "id": "glossary-099",
    "name": "TAM 분석",
    "description": "TAM(총 주소 가능 시장) 분석은 제품 또는 서비스가 가질 수 있는 전체 수익 기회를 추정하는 과정입니다. 이는 모든 잠재 고객을 포함하며, 특정 시장 세그먼트에서 기업이 100%의 시장 점유율을 달성할 경우 창출될 수 있는 최대 수요를 나타냅니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/tam-analysis/",
    "category": "비즈니스 AI & 자동화",
    "initial": "T"
  },
  {
    "id": "glossary-100",
    "name": "Top-k 정확도",
    "description": "Top-k 정확도는 머신러닝 평가 지표로, 실제 정답 클래스가 예측된 상위 k개 클래스 내에 포함되어 있는지를 평가하여, 다중 클래스 분류 작업에서 포괄적이고 관대한 측정 기준을 제공합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/top-k-accuracy/",
    "category": "머신러닝 & 딥러닝",
    "initial": "T"
  },
  {
    "id": "glossary-101",
    "name": "Torch",
    "description": "Torch는 딥러닝 및 AI 작업에 최적화된 Lua 기반의 오픈소스 머신러닝 라이브러리이자 과학 컴퓨팅 프레임워크입니다. 신경망 구축 도구를 제공하며, GPU 가속을 지원하고 PyTorch의 전신이었습니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/torch/",
    "category": "머신러닝 & 딥러닝",
    "initial": "T"
  },
  {
    "id": "glossary-102",
    "name": "Whisper",
    "description": "OpenAI Whisper는 99개 언어를 지원하며, 악센트와 소음에도 강인하고, 다양한 AI 애플리케이션에 활용할 수 있도록 오픈소스로 제공되는 고급 자동 음성 인식(ASR) 시스템입니다. 음성 언어를 텍스트로 변환합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/whisper/",
    "category": "자연어 & 멀티모달",
    "initial": "W"
  },
  {
    "id": "glossary-103",
    "name": "XAI (설명 가능한 인공지능)",
    "description": "설명 가능한 인공지능(XAI)은 AI 모델의 결과를 사람이 이해할 수 있도록 만들어 투명성, 해석 가능성, 책임성을 강화하는 다양한 방법과 프로세스의 모음입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/xai-explainable-ai/",
    "category": "머신러닝 & 딥러닝",
    "initial": "X"
  },
  {
    "id": "glossary-104",
    "name": "xAI의 Grok",
    "description": "Elon Musk가 이끄는 xAI의 첨단 AI 챗봇 Grok 모델에 대해 자세히 알아보세요. 실시간 데이터 접근, 주요 기능, 벤치마크, 활용 사례 및 다른 AI 모델과의 비교를 확인할 수 있습니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/grok-by-xai/",
    "category": "비즈니스 AI & 자동화",
    "initial": "X"
  },
  {
    "id": "glossary-105",
    "name": "XGBoost",
    "description": "XGBoost는 Extreme Gradient Boosting의 약자로, 효율적이고 확장 가능한 머신러닝 모델 학습을 위해 설계된 최적화된 분산 그레이디언트 부스팅 라이브러리입니다. 속도, 성능, 강력한 정규화 기능으로 잘 알려져 있습니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/xgboost/",
    "category": "머신러닝 & 딥러닝",
    "initial": "X"
  },
  {
    "id": "glossary-106",
    "name": "가독성",
    "description": "가독성은 독자가 작성된 텍스트를 얼마나 쉽게 이해할 수 있는지를 측정하며, 어휘, 문장 구조, 조직을 통한 명확성과 접근성을 반영합니다. 교육, 마케팅, 의료 등 다양한 분야에서 가독성의 중요성, 측정 공식, AI 도구가 가독성 향상에 어떻게 기여하는지 알아보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/readability/",
    "category": "자연어 & 멀티모달",
    "initial": "ㄱ"
  },
  {
    "id": "glossary-107",
    "name": "감정 분석",
    "description": "감정 분석(오피니언 마이닝)은 텍스트의 감정적 톤을 긍정, 부정, 중립으로 분류하고 해석하는 데 중요한 AI 및 자연어 처리(NLP) 작업입니다. 그 중요성, 유형, 접근 방식, 그리고 비즈니스에서의 실질적 활용 사례를 알아보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/sentiment-analysis/",
    "category": "자연어 & 멀티모달",
    "initial": "ㄱ"
  },
  {
    "id": "glossary-108",
    "name": "강화 학습",
    "description": "강화 학습(RL)은 에이전트가 환경 내에서 일련의 결정을 내리도록 훈련하여, 보상이나 벌점의 형태로 피드백을 받으며 최적의 행동을 학습하는 머신러닝의 한 분야입니다. 강화 학습의 핵심 개념, 알고리즘, 응용 분야 그리고 도전 과제를 살펴보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/reinforcement-learning/",
    "category": "AI 에이전트 & RAG",
    "initial": "ㄱ"
  },
  {
    "id": "glossary-109",
    "name": "강화 학습 (RL)",
    "description": "강화 학습(RL)은 에이전트가 행동을 수행하고 피드백을 받으면서 의사 결정을 학습하는 기계 학습 모델 훈련 방법입니다. 보상 또는 벌점 형태의 피드백은 에이전트가 시간이 지남에 따라 성능을 향상하도록 안내합니다. RL은 게임, 로보틱스, 금융, 헬스케어, 자율주행차 등 다양한 분야에서 널리 사용됩니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/reinforcement-learning-rl/",
    "category": "AI 에이전트 & RAG",
    "initial": "ㄱ"
  },
  {
    "id": "glossary-110",
    "name": "개인화 마케팅",
    "description": "AI 기반의 개인화 마케팅은 인공지능을 활용하여 고객의 행동, 선호도, 상호작용을 기반으로 마케팅 전략과 커뮤니케이션을 개인별로 맞춤화하여, 참여도, 만족도, 전환율을 높입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/personalized-marketing/",
    "category": "비즈니스 AI & 자동화",
    "initial": "ㄱ"
  },
  {
    "id": "glossary-111",
    "name": "개체명 인식(NER)",
    "description": "개체명 인식(NER)은 AI의 자연어 처리(NLP) 주요 하위 분야로, 텍스트 내에서 인물, 조직, 위치 등과 같은 사전 정의된 범주로 엔터티를 식별 및 분류하여 데이터 분석을 강화하고 정보 추출을 자동화합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/named-entity-recognition-ner/",
    "category": "자연어 & 멀티모달",
    "initial": "ㄱ"
  },
  {
    "id": "glossary-112",
    "name": "검색 기반 생성(RAG, Retrieval Augmented Generation)",
    "description": "검색 기반 생성(RAG, Retrieval Augmented Generation)은 전통적인 정보 검색 시스템과 생성형 대규모 언어 모델(LLM)을 결합한 고급 AI 프레임워크로, 외부 지식을 통합하여 더 정확하고 최신이며 맥락에 맞는 텍스트를 생성할 수 있도록 합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/retrieval-augmented-generation-rag/",
    "category": "AI 에이전트 & RAG",
    "initial": "ㄱ"
  },
  {
    "id": "glossary-113",
    "name": "검색 파이프라인",
    "description": "챗봇을 위한 검색 파이프라인이 무엇인지, 그 구성 요소와 활용 사례, 그리고 RAG 및 외부 데이터 소스가 어떻게 정확하고 맥락을 고려한 실시간 응답을 가능하게 하는지 알아보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/retrieval-pipeline/",
    "category": "AI 에이전트 & RAG",
    "initial": "ㄱ"
  },
  {
    "id": "glossary-114",
    "name": "결정론적 모델",
    "description": "결정론적 모델은 주어진 입력 조건 집합에 대해 단일하고 명확한 출력을 생성하는 수학적 또는 컴퓨터 모델로, 무작위성이 없이 예측 가능성과 신뢰성을 제공합니다. AI, 금융, 공학, GIS 등에서 널리 사용되며, 결정론적 모델은 정밀한 분석을 제공하지만 실제 세계의 변동성에는 유연성이 부족할 수 있습니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/deterministic-model/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㄱ"
  },
  {
    "id": "glossary-115",
    "name": "경사 하강법",
    "description": "경사 하강법은 머신러닝과 딥러닝에서 비용 함수 또는 손실 함수를 반복적으로 모델 파라미터를 조정하여 최소화하는 데 널리 사용되는 기본 최적화 알고리즘입니다. 신경망과 같은 모델 최적화에 매우 중요하며, 배치, 확률적, 미니배치 경사 하강법 등의 형태로 구현됩니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/gradient-descent/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㄱ"
  },
  {
    "id": "glossary-116",
    "name": "계층적(파싯) 검색",
    "description": "계층적(파싯) 검색은 사용자가 미리 정의된 카테고리(파싯)를 기반으로 여러 필터를 적용하여 대용량 데이터를 효율적으로 탐색하고 세분화할 수 있게 해주는 고급 검색 기법입니다. 이 방식은 전자상거래, 도서관, 엔터프라이즈 검색 등에서 널리 사용되며, 사용자가 원하는 정보를 빠르고 효율적으로 찾을 수 있도록 사용자 경험을 향상시킵니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/faceted-search/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㄱ"
  },
  {
    "id": "glossary-117",
    "name": "고객 서비스 자동화",
    "description": "고객 서비스 자동화는 AI, 챗봇, 셀프서비스 포털 및 자동화 시스템을 활용하여 최소한의 인간 개입으로 고객 문의 및 서비스 업무를 관리합니다. 이를 통해 상호작용을 간소화하고, 비용을 절감하며, 효율성을 향상시키는 동시에 인간 지원과의 균형을 유지합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/customer-service-automation/",
    "category": "비즈니스 AI & 자동화",
    "initial": "ㄱ"
  },
  {
    "id": "glossary-118",
    "name": "곡선 아래 면적 (AUC)",
    "description": "곡선 아래 면적(AUC)은 머신러닝에서 이진 분류 모델의 성능을 평가하는 데 사용되는 기본적인 지표입니다. 이는 수신자 조작 특성(ROC) 곡선 아래의 면적을 계산하여 모델이 양성 클래스와 음성 클래스를 구분하는 전체적인 능력을 정량화합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/area-under-the-curve-auc/",
    "category": "자연어 & 멀티모달",
    "initial": "ㄱ"
  },
  {
    "id": "glossary-119",
    "name": "공지시 해소(Coreference Resolution)",
    "description": "공지시 해소는 텍스트 내에서 동일한 실체를 지칭하는 표현들을 식별하고 연결하는 핵심 NLP 과제로, 요약, 번역, 질의응답 등 다양한 응용 분야에서 기계의 언어 이해에 필수적입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/coreference-resolution/",
    "category": "자연어 & 멀티모달",
    "initial": "ㄱ"
  },
  {
    "id": "glossary-120",
    "name": "과적합(Overfitting)",
    "description": "과적합은 인공지능(AI)과 머신러닝(ML)에서 매우 중요한 개념으로, 모델이 학습 데이터를 지나치게 학습하여 잡음까지 포함하게 되어 새로운 데이터에 대해 일반화 성능이 떨어지는 현상을 말합니다. 과적합을 식별하고 효과적으로 방지하는 다양한 기법을 알아보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/overfitting/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㄱ"
  },
  {
    "id": "glossary-121",
    "name": "광학 문자 인식(OCR)",
    "description": "광학 문자 인식(OCR)은 스캔된 문서, PDF 또는 이미지를 편집 가능하고 검색 가능한 데이터로 변환하는 혁신적인 기술입니다. OCR의 작동 원리, 종류, 응용 분야, 장점, 한계, 그리고 AI 기반 OCR 시스템의 최신 발전에 대해 알아보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/optical-character-recognition-ocr/",
    "category": "자연어 & 멀티모달",
    "initial": "ㄱ"
  },
  {
    "id": "glossary-122",
    "name": "교차 검증",
    "description": "교차 검증은 데이터를 여러 번 훈련 세트와 검증 세트로 나누어 머신러닝 모델을 평가하고 비교하는 통계적 방법입니다. 이를 통해 모델이 보이지 않는 데이터에도 잘 일반화되도록 하며 과적합을 방지할 수 있습니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/cross-validation/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㄱ"
  },
  {
    "id": "glossary-123",
    "name": "교통 분야의 인공지능(AI)",
    "description": "교통 분야의 인공지능(AI)은 AI 기술을 통합하여 교통 산업의 다양한 측면을 최적화, 자동화 및 개선하는 것을 의미합니다. 여기에는 기계 학습, 예측 분석, AI 기반 시스템을 활용하여 안전성 향상, 경로 최적화, 교통 관리, 자율주행 차량 구현 등 효율성과 지속 가능성을 높이는 다양한 기술이 포함됩니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/ai-in-transportation/",
    "category": "보안 & 프라이버시",
    "initial": "ㄱ"
  },
  {
    "id": "glossary-124",
    "name": "구글 코랩",
    "description": "Google Colaboratory(구글 코랩)는 구글이 제공하는 클라우드 기반 주피터 노트북 플랫폼으로, 사용자가 브라우저에서 Python 코드를 작성·실행할 수 있으며, 머신러닝과 데이터 과학에 적합하게 GPU/TPU를 무료로 이용할 수 있습니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/google-colab/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㄱ"
  },
  {
    "id": "glossary-125",
    "name": "구조화된 데이터",
    "description": "구조화된 데이터와 그 활용 방법에 대해 자세히 알아보고, 예시를 확인하며 다른 유형의 데이터 구조와 비교해보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/structured-data/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㄱ"
  },
  {
    "id": "glossary-126",
    "name": "구현된 AI 에이전트",
    "description": "구현된 AI 에이전트는 물리적 또는 가상 몸체를 통해 환경을 인지하고 해석하며 상호작용하는 지능형 시스템입니다. 이러한 에이전트가 로보틱스와 디지털 시뮬레이션에서 어떻게 동작하며, 인지, 추론, 행동이 요구되는 작업을 수행하는지 알아보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/embodied-ai-agents/",
    "category": "AI 에이전트 & RAG",
    "initial": "ㄱ"
  },
  {
    "id": "glossary-127",
    "name": "군집화",
    "description": "군집화는 비지도 학습 기법으로, 유사한 데이터 포인트들을 함께 묶어 레이블이 없는 데이터에서도 탐색적 데이터 분석을 가능하게 합니다. 군집화의 유형, 활용 분야, 임베딩 모델이 군집화에 어떻게 기여하는지 알아보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/clustering/",
    "category": "자연어 & 멀티모달",
    "initial": "ㄱ"
  },
  {
    "id": "glossary-128",
    "name": "그래디언트 부스팅",
    "description": "그래디언트 부스팅은 회귀와 분류를 위한 강력한 머신러닝 앙상블 기법입니다. 이 방법은 일반적으로 의사결정나무를 사용하여 모델을 순차적으로 구축하며, 예측을 최적화하고 정확성을 높이며 과적합을 방지합니다. 데이터 사이언스 대회와 비즈니스 솔루션에서 널리 활용됩니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/gradient-boosting/",
    "category": "비즈니스 AI & 자동화",
    "initial": "ㄱ"
  },
  {
    "id": "glossary-129",
    "name": "금융 사기 탐지",
    "description": "금융 사기 탐지에서 AI는 금융 서비스 내에서 발생하는 사기 행위를 식별하고 방지하기 위해 인공지능 기술을 적용하는 것을 의미합니다. 이러한 기술에는 기계 학습, 예측 분석, 이상 탐지 등이 포함되며, 대규모 데이터셋을 분석하여 의심스러운 거래나 일반적인 행동에서 벗어난 패턴을 식별합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/finance-fraud-detection/",
    "category": "비즈니스 AI & 자동화",
    "initial": "ㄱ"
  },
  {
    "id": "glossary-130",
    "name": "기술적 특이점",
    "description": "기술적 특이점은 인공지능(AI)이 인간의 지능을 초월하여 사회에 극적이고 예측 불가능한 변화를 가져오는 이론적인 미래의 사건입니다. 이 개념은 초지능 AI와 관련된 잠재적 이점과 중요한 위험 요소 모두를 탐구합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/technological-singularity/",
    "category": "보안 & 프라이버시",
    "initial": "ㄱ"
  },
  {
    "id": "glossary-131",
    "name": "깊이 추정",
    "description": "깊이 추정은 컴퓨터 비전에서 핵심적인 작업으로, 이미지 내 객체의 카메라로부터의 거리를 예측하는 데 중점을 둡니다. 이는 2D 이미지 데이터를 3D 공간 정보로 변환하며, 자율주행차, AR, 로봇공학, 3D 모델링과 같은 응용 분야의 기초가 됩니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/depth-estimation/",
    "category": "자연어 & 멀티모달",
    "initial": "ㄱ"
  },
  {
    "id": "glossary-132",
    "name": "나이브 베이즈",
    "description": "나이브 베이즈는 조건부 확률을 적용하는 베이즈 정리에 기반한 분류 알고리즘의 한 종류로, 각 특성들이 조건부로 독립적이라는 단순화된 가정을 사용합니다. 이러한 가정에도 불구하고 나이브 베이즈 분류기는 효과적이고 확장성이 뛰어나며, 스팸 탐지나 텍스트 분류와 같은 다양한 응용 분야에 사용됩니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/naive-bayes/",
    "category": "자연어 & 멀티모달",
    "initial": "ㄴ"
  },
  {
    "id": "glossary-133",
    "name": "네거티브 프롬프트",
    "description": "AI에서 네거티브 프롬프트는 모델이 생성하는 결과물에 포함하지 말아야 할 요소를 지시하는 명령어입니다. 전통적인 프롬프트가 콘텐츠 생성 방향을 안내하는 것과 달리, 네거티브 프롬프트는 피해야 할 요소, 스타일, 특징 등을 명확히 지정함으로써 결과물을 정교하게 다듬고, 특히 Stable Diffusion, Midjourney와 같은 생성형 모델에서 사용자의 선호에 맞게 결과를 조정하는 데 유용합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/negative-prompt/",
    "category": "LLM & 생성형 AI",
    "initial": "ㄴ"
  },
  {
    "id": "glossary-134",
    "name": "노코드",
    "description": "노코드 AI 플랫폼은 사용자가 코드를 작성하지 않고도 AI 및 머신러닝 모델을 구축, 배포, 관리할 수 있게 해줍니다. 이 플랫폼들은 시각적 인터페이스와 사전 구축된 컴포넌트를 제공하여, 비즈니스 사용자, 분석가, 도메인 전문가 등에게 AI를 민주화합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/no-code/",
    "category": "비즈니스 AI & 자동화",
    "initial": "ㄴ"
  },
  {
    "id": "glossary-135",
    "name": "뉴로모픽 컴퓨팅",
    "description": "뉴로모픽 컴퓨팅은 하드웨어와 소프트웨어 요소를 인간의 뇌와 신경계에서 모델링하는 최첨단 컴퓨터 공학 접근 방식입니다. 뉴로모픽 엔지니어링이라고도 하는 이 학제간 분야는 컴퓨터 과학, 생물학, 수학, 전자 공학, 물리학을 아우르며 생체 영감을 받은 컴퓨터 시스템과 하드웨어를 만듭니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/neuromorphic-computing/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㄴ"
  },
  {
    "id": "glossary-136",
    "name": "달-이(DALL-E)",
    "description": "DALL-E는 OpenAI가 개발한 텍스트-이미지 생성 AI 모델 시리즈로, 딥러닝을 활용해 텍스트 설명으로부터 디지털 이미지를 생성합니다. 역사, 예술·마케팅·교육 분야 활용, 윤리적 고려 사항 등에 대해 알아보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/dall-e/",
    "category": "자연어 & 멀티모달",
    "initial": "ㄷ"
  },
  {
    "id": "glossary-137",
    "name": "대시(Dash)",
    "description": "Dash는 Plotly에서 개발한 오픈소스 파이썬 프레임워크로, Flask, React.js, Plotly.js를 결합해 상호작용적인 데이터 시각화 애플리케이션과 대시보드를 쉽고 원활하게 구축할 수 있는 분석 및 비즈니스 인텔리전스 솔루션을 제공합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/dash/",
    "category": "비즈니스 AI & 자동화",
    "initial": "ㄷ"
  },
  {
    "id": "glossary-138",
    "name": "대형 언어 모델 (LLM)",
    "description": "대형 언어 모델(LLM)은 방대한 텍스트 데이터를 학습하여 인간 언어를 이해하고 생성하며 조작할 수 있도록 설계된 인공지능의 한 종류입니다. LLM은 딥러닝과 트랜스포머 신경망을 활용해 텍스트 생성, 요약, 번역 등 다양한 산업 분야의 업무를 지원합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/large-language-model-llm/",
    "category": "LLM & 생성형 AI",
    "initial": "ㄷ"
  },
  {
    "id": "glossary-139",
    "name": "대형 언어 모델 메타 AI (LLaMA)",
    "description": "대형 언어 모델 메타 AI (LLaMA)는 Meta에서 개발한 최첨단 자연어 처리 모델입니다. 최대 650억 개의 파라미터를 보유한 LLaMA는 번역, 요약, 챗봇 등 다양한 작업에서 인간과 유사한 텍스트 이해 및 생성에 뛰어납니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/large-language-model-meta-ai-llama/",
    "category": "LLM & 생성형 AI",
    "initial": "ㄷ"
  },
  {
    "id": "glossary-140",
    "name": "대화형 AI",
    "description": "대화형 AI는 자연어 처리(NLP), 머신러닝, 기타 언어 기술을 활용하여 컴퓨터가 인간의 대화를 모방할 수 있게 하는 기술을 의미합니다. 이는 챗봇, 가상 비서, 음성 비서를 고객 지원, 의료, 소매 등 다양한 분야에 적용하여 효율성과 개인화를 향상시킵니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/conversational-ai/",
    "category": "자연어 & 멀티모달",
    "initial": "ㄷ"
  },
  {
    "id": "glossary-141",
    "name": "데이터 거버넌스",
    "description": "데이터 거버넌스는 조직 내에서 데이터의 효과적이고 효율적인 사용, 가용성, 무결성, 보안을 보장하는 프로세스, 정책, 역할, 표준의 프레임워크입니다. 업계 전반에 걸쳐 컴플라이언스, 의사결정, 데이터 품질을 주도합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/data-governance/",
    "category": "보안 & 프라이버시",
    "initial": "ㄷ"
  },
  {
    "id": "glossary-142",
    "name": "데이터 검증",
    "description": "AI에서 데이터 검증은 AI 모델을 학습하고 테스트하는 데 사용되는 데이터의 품질, 정확성, 신뢰성을 평가하고 보장하는 과정을 말합니다. 이는 모델 성능과 신뢰성을 높이기 위해 불일치, 오류 또는 이상값을 식별하고 수정하는 작업을 포함합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/data-validation/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㄷ"
  },
  {
    "id": "glossary-143",
    "name": "데이터 마이닝",
    "description": "데이터 마이닝은 방대한 원시 데이터를 분석하여 패턴, 관계, 통찰을 발견함으로써 비즈니스 전략과 의사결정에 활용하는 고도화된 과정입니다. 고급 분석 기법을 활용해 조직이 트렌드를 예측하고, 고객 경험을 향상시키며, 운영 효율성을 개선하도록 돕습니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/data-mining/",
    "category": "비즈니스 AI & 자동화",
    "initial": "ㄷ"
  },
  {
    "id": "glossary-144",
    "name": "데이터 보호 규정",
    "description": "데이터 보호 규정은 전 세계적으로 개인 데이터의 보안, 처리 관리, 그리고 개인의 프라이버시 권리를 보호하는 법적 프레임워크, 정책, 기준입니다. 이러한 규정은 준수를 보장하고, 무단 접근을 방지하며, 디지털 시대에서 데이터 주체의 권리를 지키도록 합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/data-protection-regulations/",
    "category": "보안 & 프라이버시",
    "initial": "ㄷ"
  },
  {
    "id": "glossary-145",
    "name": "데이터 부족",
    "description": "데이터 부족은 머신러닝 모델 학습이나 종합적인 분석에 충분한 데이터가 없어 정확한 AI 시스템 개발을 저해하는 현상입니다. 데이터 부족의 원인, 영향, 그리고 AI 및 자동화에서 이를 극복하는 기술을 알아보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/data-scarcity/",
    "category": "비즈니스 AI & 자동화",
    "initial": "ㄷ"
  },
  {
    "id": "glossary-146",
    "name": "데이터 정제",
    "description": "데이터 정제는 데이터의 오류나 불일치 사항을 탐지하고 수정하는 중요한 과정으로, 데이터의 품질을 높여 분석 및 의사결정을 위한 정확성, 일관성, 신뢰성을 보장합니다. 주요 프로세스, 과제, 도구, 그리고 효과적인 데이터 정제에서 AI와 자동화의 역할을 알아보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/data-cleaning/",
    "category": "비즈니스 AI & 자동화",
    "initial": "ㄷ"
  },
  {
    "id": "glossary-147",
    "name": "데이터로봇",
    "description": "데이터로봇은 기계 학습 모델의 생성, 배포 및 관리를 간소화하는 종합 AI 플랫폼으로, 예측 및 생성형 AI를 모든 기술 수준의 사용자가 쉽게 활용할 수 있게 해줍니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/datarobot/",
    "category": "LLM & 생성형 AI",
    "initial": "ㄷ"
  },
  {
    "id": "glossary-148",
    "name": "드롭아웃",
    "description": "드롭아웃은 AI, 특히 신경망에서 과적합을 방지하기 위해 훈련 중 무작위로 뉴런을 비활성화하여 견고한 특성 학습과 새로운 데이터에 대한 일반화 능력을 향상시키는 정규화 기법입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/dropout/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㄷ"
  },
  {
    "id": "glossary-149",
    "name": "딥 신념망(Deep Belief Networks, DBNs)",
    "description": "딥 신념망(DBN)은 깊은 아키텍처와 제한 볼츠만 머신(RBM)을 활용하여 이미지 및 음성 인식과 같은 지도 및 비지도 작업 모두를 위한 계층적 데이터 표현을 학습하는 정교한 생성 모델입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/deep-belief-networks-dbns/",
    "category": "자연어 & 멀티모달",
    "initial": "ㄷ"
  },
  {
    "id": "glossary-150",
    "name": "딥러닝",
    "description": "딥러닝은 인공지능(AI)에서 기계학습의 한 분야로, 인간 두뇌의 데이터 처리 및 의사결정 패턴 생성 방식을 모방합니다. 이는 인공신경망이라 불리는 뇌의 구조와 기능에서 영감을 받았습니다. 딥러닝 알고리즘은 복잡한 데이터 관계를 분석하고 해석하여 음성 인식, 이미지 분류, 복잡한 문제 해결 등 높은 정확도로 다양한 작업을 가능하게 합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/deep-learning/",
    "category": "자연어 & 멀티모달",
    "initial": "ㄷ"
  },
  {
    "id": "glossary-151",
    "name": "딥페이크",
    "description": "딥페이크는 AI를 활용해 매우 사실적으로 보이지만 가짜인 이미지, 비디오, 오디오 녹음을 생성하는 합성 미디어의 한 형태입니다. “딥페이크”라는 용어는 “딥러닝(deep learning)”과 “페이크(fake)”의 합성어로, 이 기술이 고도화된 머신러닝 기법에 의존함을 반영합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/deepfake/",
    "category": "자연어 & 멀티모달",
    "initial": "ㄷ"
  },
  {
    "id": "glossary-152",
    "name": "라이터(Writer)",
    "description": "Writer.ai는 마케팅 자료, 블로그 게시물, 이메일 등 다양한 글쓰기 과정을 간소화하고 향상시키도록 설계된 AI 기반 콘텐츠 생성 도구로, 브랜드 일관성과 효율적이며 고품질의 콘텐츠 제작을 보장합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/writer/",
    "category": "비즈니스 AI & 자동화",
    "initial": "ㄹ"
  },
  {
    "id": "glossary-153",
    "name": "라이트소닉",
    "description": "Writesonic에 대한 기본 정보를 알아보세요. 주요 기능, 장단점, 그리고 대안에 대한 빠른 개요를 제공합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/writesonic/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㄹ"
  },
  {
    "id": "glossary-154",
    "name": "랜덤 포레스트 회귀",
    "description": "랜덤 포레스트 회귀는 예측 분석에 사용되는 강력한 머신러닝 알고리즘입니다. 여러 개의 의사결정나무를 구축하고 그 결과를 평균화하여 다양한 산업 분야에서 정확성, 견고성, 다양성을 높입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/random-forest-regression/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㄹ"
  },
  {
    "id": "glossary-155",
    "name": "렉사일 프레임워크",
    "description": "렉사일 프레임워크는 독자의 읽기 능력과 텍스트의 복잡도를 동일한 발달 척도에서 측정하는 과학적 방법으로, 독자에게 적합한 난이도의 텍스트를 매칭하여 읽기 성장을 촉진합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/lexile-framework/",
    "category": "자연어 & 멀티모달",
    "initial": "ㄹ"
  },
  {
    "id": "glossary-156",
    "name": "로그 손실",
    "description": "로그 손실(로그라리즘/크로스 엔트로피 손실)은 머신러닝 모델의 성능을 평가하는 핵심 지표로, 특히 이진 분류에서 예측 확률과 실제 결과의 차이를 측정하여 잘못되거나 과도하게 확신하는 예측에 패널티를 부여합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/log-loss/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㄹ"
  },
  {
    "id": "glossary-157",
    "name": "로지스틱 회귀",
    "description": "로지스틱 회귀는 데이터를 기반으로 이진 결과를 예측하는 통계 및 머신러닝 기법입니다. 하나 이상의 독립 변수에 따라 사건이 발생할 확률을 추정하며, 의료, 금융, 마케팅, AI 등 다양한 분야에 널리 적용됩니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/logistic-regression/",
    "category": "비즈니스 AI & 자동화",
    "initial": "ㄹ"
  },
  {
    "id": "glossary-158",
    "name": "리드 라우팅",
    "description": "리드 라우팅은 잠재 고객을 위치, 제품 관심사, 전문성 등과 같은 기준에 따라 적합한 영업 담당자에게 자동으로 배정하여, 가장 알맞은 담당자와 연결해주는 프로세스입니다. 자동화와 AI가 리드 분배를 어떻게 최적화하여 전환율과 고객 경험을 높이는지 알아보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/lead-routing/",
    "category": "비즈니스 AI & 자동화",
    "initial": "ㄹ"
  },
  {
    "id": "glossary-159",
    "name": "리드 스크레이퍼",
    "description": "리드 스크레이핑은 온라인 소스에서 가치 있는 연락처 데이터를 자동으로 추출하여, 비즈니스가 타겟 마케팅과 영업을 위한 고품질 리드 데이터베이스를 효율적으로 구축하도록 하며, 데이터 프라이버시 준수를 보장합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/lead-scraper/",
    "category": "보안 & 프라이버시",
    "initial": "ㄹ"
  },
  {
    "id": "glossary-160",
    "name": "리테일 분야의 AI",
    "description": "리테일 분야의 인공지능(AI)은 머신러닝, 자연어 처리(NLP), 컴퓨터 비전, 로보틱스와 같은 첨단 기술을 활용하여 고객 경험을 향상시키고, 재고를 최적화하며, 공급망을 효율화하고, 운영 효율성을 높입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/ai-in-retail/",
    "category": "자연어 & 멀티모달",
    "initial": "ㄹ"
  },
  {
    "id": "glossary-161",
    "name": "매개변수 효율적 미세 조정(PEFT)",
    "description": "매개변수 효율적 미세 조정(PEFT)은 대규모 사전 학습 모델을 특정 작업에 맞게 적은 수의 매개변수만을 업데이트하여 적응할 수 있게 하는 AI 및 NLP 분야의 혁신적인 접근법입니다. 이를 통해 연산 비용과 학습 시간을 줄이며 효율적으로 모델을 배포할 수 있습니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/parameter-efficient-fine-tuning-peft/",
    "category": "LLM & 생성형 AI",
    "initial": "ㅁ"
  },
  {
    "id": "glossary-162",
    "name": "머신러닝",
    "description": "머신러닝(ML)은 인공지능(AI)의 한 분야로, 기계가 데이터를 통해 학습하고 패턴을 식별하며 예측을 하고, 명시적인 프로그래밍 없이도 시간이 지남에 따라 의사결정을 개선할 수 있도록 합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/machine-learning/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅁ"
  },
  {
    "id": "glossary-163",
    "name": "머신러닝 파이프라인",
    "description": "머신러닝 파이프라인은 원시 데이터를 실용적인 인사이트로 효율적이고 대규모로 전환하는 머신러닝 모델의 개발, 학습, 평가, 배포 과정을 자동화하여 표준화하는 워크플로우입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/machine-learning-pipeline/",
    "category": "AI 에이전트 & RAG",
    "initial": "ㅁ"
  },
  {
    "id": "glossary-164",
    "name": "머신러닝에서의 리콜(Recall)",
    "description": "머신러닝에서의 리콜(Recall)에 대해 알아보세요. 분류 작업에서 모델 성능을 평가하는 데 중요한 이 지표는 양성 인스턴스를 올바르게 식별하는 것이 얼마나 중요한지 설명합니다. 정의, 계산 방법, 중요성, 활용 사례, 개선 전략까지 모두 확인해보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/recall-in-machine-learning/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅁ"
  },
  {
    "id": "glossary-165",
    "name": "멀티홉 추론",
    "description": "멀티홉 추론은 AI, 특히 자연어 처리(NLP)와 지식 그래프 분야에서 시스템이 복잡한 질문에 답하거나 결정을 내리기 위해 여러 정보를 연결하는 과정입니다. 이는 데이터 소스 간의 논리적 연결을 가능하게 하여, 고급 질문 응답, 지식 그래프 완성, 그리고 더욱 똑똑한 챗봇을 지원합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/multi-hop-reasoning/",
    "category": "자연어 & 멀티모달",
    "initial": "ㅁ"
  },
  {
    "id": "glossary-166",
    "name": "메타프롬프트",
    "description": "인공지능에서 메타프롬프트란 대형 언어 모델(LLM)을 위한 다른 프롬프트를 생성하거나 개선하도록 설계된 상위 수준의 지침으로, AI 출력 향상, 작업 자동화, 챗봇 및 자동화 워크플로우에서의 다단계 추론을 개선합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/metaprompt/",
    "category": "AI 에이전트 & RAG",
    "initial": "ㅁ"
  },
  {
    "id": "glossary-167",
    "name": "모델 견고성",
    "description": "모델 견고성은 머신러닝(ML) 모델이 입력 데이터의 변동성과 불확실성에도 불구하고 일관되고 정확한 성능을 유지하는 능력을 의미합니다. 견고한 모델은 신뢰할 수 있는 AI 애플리케이션을 위해 필수적이며, 노이즈, 이상치, 분포 변화, 적대적 공격에도 탄력성을 보장합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/model-robustness/",
    "category": "보안 & 프라이버시",
    "initial": "ㅁ"
  },
  {
    "id": "glossary-168",
    "name": "모델 드리프트",
    "description": "모델 드리프트(또는 모델 붕괴)는 실제 환경의 변화로 인해 머신러닝 모델의 예측 성능이 시간이 지남에 따라 저하되는 현상을 의미합니다. AI 및 머신러닝에서 모델 드리프트의 유형, 원인, 탐지 방법, 해결책에 대해 알아보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/model-drift/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅁ"
  },
  {
    "id": "glossary-169",
    "name": "모델 붕괴",
    "description": "모델 붕괴는 인공지능에서 훈련된 모델이 시간이 지나면서 특히 합성 데이터나 AI가 생성한 데이터에 의존할 때 성능이 저하되는 현상입니다. 이로 인해 출력 다양성이 감소하고, 안전한 답변이 많아지며, 창의적이거나 독창적인 콘텐츠를 생성하는 능력이 저하됩니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/model-collapse/",
    "category": "보안 & 프라이버시",
    "initial": "ㅁ"
  },
  {
    "id": "glossary-170",
    "name": "모델 체이닝",
    "description": "모델 체이닝은 여러 모델을 순차적으로 연결하여 각각의 모델 출력이 다음 모델의 입력이 되는 머신러닝 기법입니다. 이 접근 방식은 AI, LLM, 그리고 엔터프라이즈 애플리케이션에서 복잡한 작업을 위한 모듈성, 유연성, 확장성을 높여줍니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/model-chaining/",
    "category": "LLM & 생성형 AI",
    "initial": "ㅁ"
  },
  {
    "id": "glossary-171",
    "name": "모델 해석 가능성",
    "description": "모델 해석 가능성은 기계 학습 모델이 내린 예측과 결정의 근거를 이해하고 설명하며 신뢰할 수 있는 능력을 의미합니다. 이는 AI에서 매우 중요하며, 특히 의료, 금융, 자율 시스템 등에서의 의사결정에 필수적입니다. 복잡한 모델과 인간의 이해 사이의 간극을 연결하는 역할을 합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/model-interpretability/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅁ"
  },
  {
    "id": "glossary-172",
    "name": "몬테카를로 방법",
    "description": "몬테카를로 방법은 반복적인 무작위 샘플링을 통해 복잡하고 종종 결정론적인 문제를 해결하는 계산 알고리즘입니다. 금융, 공학, AI 등 다양한 분야에서 널리 사용되며, 다양한 시나리오를 시뮬레이션하고 확률적 결과를 분석함으로써 불확실성 모델링, 최적화, 위험 평가를 가능하게 합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/monte-carlo-methods/",
    "category": "보안 & 프라이버시",
    "initial": "ㅁ"
  },
  {
    "id": "glossary-173",
    "name": "문단 리라이팅 도구",
    "description": "문단 리라이팅 도구가 무엇인지, 어떻게 작동하는지, 주요 기능과 고급 언어 처리 기술을 통해 글쓰기 품질 향상, 표절 방지, SEO 강화에 어떻게 기여하는지 알아보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/paragraph-rewriter/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅁ"
  },
  {
    "id": "glossary-174",
    "name": "문서 등급 평가",
    "description": "검색 증강 생성(RAG)에서 문서 등급 평가는 쿼리에 대한 관련성과 품질을 기준으로 문서를 평가하고 순위를 매기는 과정으로, 가장 적합하고 고품질의 문서만을 사용하여 정확하고 문맥을 고려한 응답을 생성하도록 보장합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/document-grading/",
    "category": "AI 에이전트 & RAG",
    "initial": "ㅁ"
  },
  {
    "id": "glossary-175",
    "name": "문서 재정렬(Document Reranking)",
    "description": "문서 재정렬은 사용자의 쿼리와의 관련성에 따라 검색된 문서의 순서를 다시 정렬하여, 가장 중요한 정보를 우선시하도록 검색 결과를 세밀하게 다듬는 과정입니다. 이는 RAG(검색 증강 생성) 시스템에서 핵심적인 단계로, 쿼리 확장과 결합되어 AI 기반 검색 및 챗봇의 재현율과 정밀도를 모두 높이는 데 활용됩니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/document-reranking/",
    "category": "AI 에이전트 & RAG",
    "initial": "ㅁ"
  },
  {
    "id": "glossary-176",
    "name": "문장 리라이팅 도구",
    "description": "AI 문장 리라이팅 도구가 무엇인지, 어떻게 작동하는지, 사용 사례는 무엇이며, 작가, 학생, 마케터가 의미를 보존하면서도 명확성을 높여 텍스트를 변환하는 데 어떻게 도움이 되는지 알아보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/sentence-rewriter/",
    "category": "자연어 & 멀티모달",
    "initial": "ㅁ"
  },
  {
    "id": "glossary-177",
    "name": "미스트랄 AI",
    "description": "미스트랄 AI와 그들이 제공하는 LLM 모델에 대해 알아보세요. 이러한 모델이 어떻게 사용되는지, 그리고 무엇이 이들을 특별하게 만드는지 확인해보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/mistral-ai/",
    "category": "LLM & 생성형 AI",
    "initial": "ㅁ"
  },
  {
    "id": "glossary-178",
    "name": "바이브 코딩",
    "description": "바이브 코딩을 발견해보세요: AI 기반 도구들이 누구나 아이디어를 코드로 바꿀 수 있게 하여 앱 개발을 더 빠르고, 더 쉽고, 창의적으로 만듭니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/vibe-coding/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅂ"
  },
  {
    "id": "glossary-179",
    "name": "발달 읽기 평가(DRA)",
    "description": "발달 읽기 평가(DRA)는 학생의 읽기 능력을 평가하기 위해 개별적으로 실시되는 도구로, 읽기 수준, 유창성, 이해력에 대한 통찰을 제공합니다. 이를 통해 교사는 유치원부터 중학교 2학년까지 맞춤형 수업을 설계하고 학습 성과를 모니터링할 수 있습니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/developmental-reading-assessment-dra/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅂ"
  },
  {
    "id": "glossary-180",
    "name": "배깅(Bagging)",
    "description": "배깅(Bagging, Bootstrap Aggregating의 약자)은 AI 및 머신러닝에서 모델의 정확성과 견고함을 높이기 위해 부트스트랩 데이터 하위 집합에 여러 기본 모델을 학습시키고 이들의 예측을 집계하는 기본 앙상블 학습 기법입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/bagging/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅂ"
  },
  {
    "id": "glossary-181",
    "name": "배치 정규화",
    "description": "배치 정규화는 딥러닝에서 내부 공변량 변화 문제를 해결하고, 활성화값을 안정화하며, 더 빠르고 안정적인 학습을 가능하게 하여 신경망의 학습 과정을 크게 향상시키는 혁신적인 기법입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/batch-normalization/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅂ"
  },
  {
    "id": "glossary-182",
    "name": "버티컬 AI 에이전트",
    "description": "버티컬 AI 에이전트는 특정 산업의 고유한 과제를 해결하고 프로세스를 최적화하기 위해 설계된 산업 특화 인공지능 솔루션입니다. 버티컬 AI 에이전트가 전문적이고 높은 임팩트를 지닌 응용 프로그램으로 엔터프라이즈 소프트웨어를 어떻게 혁신하는지 알아보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/vertical-ai-agent/",
    "category": "AI 에이전트 & RAG",
    "initial": "ㅂ"
  },
  {
    "id": "glossary-183",
    "name": "범용 인공지능(AGI)",
    "description": "범용 인공지능(AGI)은 인간과 유사한 수준에서 다양한 작업을 이해하고, 학습하며, 지식을 적용할 수 있는 이론적 형태의 AI로, 좁은 AI와는 다릅니다. AGI의 정의, 핵심 특성, 현재 상태, 연구 방향을 살펴보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/artificial-general-intelligence-agi/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅂ"
  },
  {
    "id": "glossary-184",
    "name": "법률 문서 검토",
    "description": "법률 문서 검토에서의 인공지능(AI)은 법률 전문가들이 법률 절차에 내재된 방대한 문서량을 처리하는 방식에 큰 변화를 가져오고 있습니다. 기계 학습, 자연어 처리(NLP), 광학 문자 인식(OCR)과 같은 AI 기술을 활용함으로써, 법률 업계는 문서 처리의 효율성, 정확성, 속도가 크게 향상되는 경험을 하고 있습니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/legal-document-review/",
    "category": "자연어 & 멀티모달",
    "initial": "ㅂ"
  },
  {
    "id": "glossary-185",
    "name": "베이즈 네트워크",
    "description": "베이즈 네트워크(BN)는 변수와 그들의 조건부 의존성을 방향성 비순환 그래프(DAG)를 통해 표현하는 확률 그래프 모델입니다. 베이즈 네트워크는 불확실성을 모델링하고 추론 및 학습을 지원하며, 의료, AI, 금융 등 다양한 분야에서 널리 사용됩니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/bayesian-networks/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅂ"
  },
  {
    "id": "glossary-186",
    "name": "벤치마킹",
    "description": "AI 모델의 벤치마킹은 표준화된 데이터셋, 작업, 성능 지표를 사용하여 인공지능 모델을 체계적으로 평가하고 비교하는 과정입니다. 이는 객관적인 평가, 모델 비교, 발전 추적을 가능하게 하며, AI 개발에서 투명성과 표준화를 촉진합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/benchmarking/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅂ"
  },
  {
    "id": "glossary-187",
    "name": "부스팅",
    "description": "부스팅은 여러 개의 약한 학습자의 예측을 결합하여 강한 학습자를 만드는 머신러닝 기법으로, 정확도를 향상시키고 복잡한 데이터를 처리합니다. 주요 알고리즘, 장점, 도전 과제, 실제 적용 사례를 알아보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/boosting/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅂ"
  },
  {
    "id": "glossary-188",
    "name": "분류기",
    "description": "AI 분류기는 기계 학습 알고리즘으로, 입력 데이터를 클래스 레이블에 할당하여 과거 데이터에서 학습한 패턴을 기반으로 정보를 미리 정의된 클래스에 분류합니다. 분류기는 AI 및 데이터 과학의 핵심 도구로, 다양한 산업에서 의사결정을 지원합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/classifier/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅂ"
  },
  {
    "id": "glossary-189",
    "name": "비정형 데이터",
    "description": "비정형 데이터가 무엇인지, 구조화된 데이터와 어떻게 다른지 알아보세요. 비정형 데이터의 과제와 활용되는 도구에 대해 배웁니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/unstructured-data/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅂ"
  },
  {
    "id": "glossary-190",
    "name": "비지도 학습",
    "description": "비지도 학습은 레이블이 없는 데이터에 알고리즘을 학습시켜 숨겨진 패턴, 구조, 관계를 발견하는 머신러닝 기법입니다. 대표적인 방법으로는 클러스터링, 연관 규칙, 차원 축소가 있으며, 고객 세분화, 이상 탐지, 장바구니 분석 등에 활용됩니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/unsupervised-learning/",
    "category": "비즈니스 AI & 자동화",
    "initial": "ㅂ"
  },
  {
    "id": "glossary-191",
    "name": "사이버보안에서의 AI",
    "description": "사이버보안에서의 인공지능(AI)은 기계 학습과 자연어 처리(NLP)와 같은 AI 기술을 활용하여 사이버 위협을 탐지, 예방 및 대응하며, 대응 자동화, 데이터 분석, 위협 인텔리전스 강화를 통해 견고한 디지털 방어체계를 구축합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/ai-in-cybersecurity/",
    "category": "보안 & 프라이버시",
    "initial": "ㅅ"
  },
  {
    "id": "glossary-192",
    "name": "사이킷런(Scikit-learn)",
    "description": "Scikit-learn은 파이썬을 위한 강력한 오픈소스 머신러닝 라이브러리로, 예측 데이터 분석을 위한 간단하고 효율적인 도구들을 제공합니다. 데이터 과학자와 머신러닝 실무자들이 널리 사용하는 이 라이브러리는 분류, 회귀, 클러스터링 등 다양한 알고리즘을 제공하며, 파이썬 생태계와의 매끄러운 통합을 자랑합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/scikit-learn/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅅ"
  },
  {
    "id": "glossary-193",
    "name": "생성 엔진 최적화(GEO)",
    "description": "생성 엔진 최적화(GEO)는 ChatGPT, Bard와 같은 AI 플랫폼에서 콘텐츠의 가시성과 정확한 표현을 보장하기 위해 최적화하는 전략입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/generative-engine-optimization-geo/",
    "category": "LLM & 생성형 AI",
    "initial": "ㅅ"
  },
  {
    "id": "glossary-194",
    "name": "생성적 적대 신경망(GAN)",
    "description": "생성적 적대 신경망(GAN)은 두 개의 신경망(생성자와 판별자)이 실제 데이터와 구별할 수 없는 데이터를 생성하기 위해 경쟁하는 기계 학습 프레임워크입니다. 2014년 Ian Goodfellow에 의해 도입된 GAN은 이미지 생성, 데이터 증강, 이상 탐지 등 다양한 분야에서 널리 사용됩니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/generative-adversarial-network-gan/",
    "category": "자연어 & 멀티모달",
    "initial": "ㅅ"
  },
  {
    "id": "glossary-195",
    "name": "생성형 AI (Gen AI)",
    "description": "생성형 AI는 텍스트, 이미지, 음악, 코드, 비디오 등 새로운 콘텐츠를 생성할 수 있는 인공지능 알고리즘의 한 범주를 말합니다. 전통적인 AI와 달리, 생성형 AI는 학습한 데이터를 바탕으로 창의적이고 자동화된 다양한 산업 분야에서 원본 결과물을 만들어냅니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/generative-ai/",
    "category": "LLM & 생성형 AI",
    "initial": "ㅅ"
  },
  {
    "id": "glossary-196",
    "name": "생성형 사전 학습 변환기(GPT)",
    "description": "생성형 사전 학습 변환기(GPT)는 딥러닝 기술을 활용하여 인간의 글쓰기를 매우 흉내내는 텍스트를 생성하는 AI 모델입니다. 트랜스포머 아키텍처를 기반으로 하며, GPT는 효율적인 텍스트 처리와 생성을 위해 자기 주의 메커니즘을 사용하여 콘텐츠 생성 및 챗봇과 같은 NLP 애플리케이션에 혁신을 가져왔습니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/generative-pre-trained-transformer-gpt/",
    "category": "LLM & 생성형 AI",
    "initial": "ㅅ"
  },
  {
    "id": "glossary-197",
    "name": "선형 회귀",
    "description": "선형 회귀는 통계와 머신러닝에서 종속 변수와 독립 변수 간의 관계를 모델링하는 핵심 분석 기법입니다. 단순성과 해석 용이성으로 잘 알려져 있으며, 예측 분석과 데이터 모델링의 기초가 됩니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/linear-regression/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅅ"
  },
  {
    "id": "glossary-198",
    "name": "설명 가능성(Explainability)",
    "description": "AI 설명 가능성은 인공지능 시스템이 내리는 결정과 예측을 이해하고 해석할 수 있는 능력을 의미합니다. AI 모델이 점점 더 복잡해짐에 따라, 설명 가능성은 LIME 및 SHAP과 같은 기법을 통해 투명성, 신뢰, 규제 준수, 편향 완화 및 모델 최적화를 보장합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/explainability/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅅ"
  },
  {
    "id": "glossary-199",
    "name": "수렴(Convergence)",
    "description": "AI에서의 수렴은 기계 학습 및 딥러닝 모델이 반복 학습을 통해 안정된 상태에 도달하여 예측값과 실제 결과 사이의 차이(손실 함수)를 최소화함으로써 정확한 예측을 보장하는 과정을 의미합니다. 이는 자율주행차부터 스마트시티에 이르기까지 다양한 응용 분야에서 AI의 효과성과 신뢰성을 뒷받침하는 기본 요소입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/convergence/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅅ"
  },
  {
    "id": "glossary-200",
    "name": "수정된 결정계수(Adjusted R-squared)",
    "description": "수정된 결정계수는 회귀 모델의 적합도를 평가하는 통계적 지표로, 예측 변수의 수를 반영하여 과적합을 방지하고 모델 성능을 보다 정확하게 평가할 수 있도록 합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/adjusted-r-squared/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅅ"
  },
  {
    "id": "glossary-201",
    "name": "순수 신규 비즈니스",
    "description": "순수 신규 비즈니스(Net New Business)는 특정 기간 내에 새로 유입된 고객 또는 재활성화된 계정에서 발생한 매출을 의미하며, 기존 활성 고객에 대한 업셀링이나 교차 판매 매출은 일반적으로 제외됩니다. 이는 기존 고객에게 추가 판매에만 의존하지 않고 고객 기반 확장에 의해 주도되는 성장을 측정하려는 기업에게 중요한 지표입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/net-new-business/",
    "category": "비즈니스 AI & 자동화",
    "initial": "ㅅ"
  },
  {
    "id": "glossary-202",
    "name": "순환 신경망 (RNN)",
    "description": "순환 신경망(RNN)은 이전 입력값을 기억하는 메모리 기능을 활용하여 순차 데이터를 처리하도록 설계된 정교한 인공 신경망의 한 종류입니다. RNN은 데이터의 순서가 중요한 작업, 예를 들어 자연어 처리(NLP), 음성 인식, 시계열 예측 등에서 뛰어난 성능을 보입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/recurrent-neural-network-rnn/",
    "category": "자연어 & 멀티모달",
    "initial": "ㅅ"
  },
  {
    "id": "glossary-203",
    "name": "스테이블 디퓨전",
    "description": "스테이블 디퓨전은 심층 학습을 활용하여 텍스트 설명만으로 고품질의 사실적인 이미지를 생성하는 첨단 텍스트-이미지 생성 모델입니다. 잠복 디퓨전 모델로서, 디퓨전 모델과 머신러닝을 효율적으로 결합하여 주어진 프롬프트에 매우 근접한 이미지를 만들어내는 생성형 AI 분야의 중요한 혁신입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/stable-diffusion/",
    "category": "LLM & 생성형 AI",
    "initial": "ㅅ"
  },
  {
    "id": "glossary-204",
    "name": "시맨틱 세그멘테이션",
    "description": "시맨틱 세그멘테이션은 이미지를 여러 영역으로 분할하여 각 픽셀에 객체 또는 영역을 나타내는 클래스 레이블을 할당하는 컴퓨터 비전 기술입니다. 이 기술은 자율주행, 의료 영상, 로보틱스 등에서 CNN, FCN, U-Net, DeepLab과 같은 딥러닝 모델을 통해 정밀한 이해를 가능하게 합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/semantic-segmentation/",
    "category": "자연어 & 멀티모달",
    "initial": "ㅅ"
  },
  {
    "id": "glossary-205",
    "name": "시퀀스 모델링",
    "description": "AI와 머신러닝에서 시퀀스 모델링을 알아보세요—RNN, LSTM, GRU, 트랜스포머를 이용해 텍스트, 오디오, DNA와 같은 데이터 시퀀스를 예측하고 생성합니다. 핵심 개념, 응용 분야, 과제, 최신 연구 동향을 살펴봅니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/sequence-modeling/",
    "category": "자연어 & 멀티모달",
    "initial": "ㅅ"
  },
  {
    "id": "glossary-206",
    "name": "식별 모델",
    "description": "식별 AI 모델에 대해 알아보세요—클래스 간의 결정 경계를 모델링함으로써 분류와 회귀에 집중하는 머신러닝 모델입니다. 동작 방식, 장점, 과제, 그리고 NLP, 컴퓨터 비전, AI 자동화에서의 적용 사례를 이해할 수 있습니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/discriminative-models/",
    "category": "자연어 & 멀티모달",
    "initial": "ㅅ"
  },
  {
    "id": "glossary-207",
    "name": "신경망",
    "description": "신경망(Neural Network) 또는 인공 신경망(ANN)은 인간 두뇌에서 영감을 받은 계산 모델로, 패턴 인식, 의사 결정, 딥러닝 애플리케이션과 같은 작업에서 인공지능(AI)과 머신러닝(ML)에 필수적입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/neural-networks/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅅ"
  },
  {
    "id": "glossary-208",
    "name": "쓰레기 입력, 쓰레기 출력(GIGO)",
    "description": "Garbage In, Garbage Out(GIGO)는 AI 및 기타 시스템의 출력 품질이 입력 품질에 직접적으로 달려 있음을 강조합니다. AI에서의 의미, 데이터 품질의 중요성, 더 정확하고 공정하며 신뢰할 수 있는 결과를 위해 GIGO를 완화하는 전략에 대해 알아보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/garbage-in-garbage-out-gigo/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅆ"
  },
  {
    "id": "glossary-209",
    "name": "아나콘다 라이브러리",
    "description": "아나콘다는 파이썬과 R의 패키지 관리 및 배포를 간소화하여 과학 컴퓨팅, 데이터 과학, 머신러닝을 위한 종합적인 오픈 소스 배포판입니다. 아나콘다 주식회사에서 개발했으며, 데이터 과학자, 개발자, IT 팀을 위한 다양한 도구를 제공하는 강력한 플랫폼입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/anaconda-library/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-210",
    "name": "알고리즘 투명성",
    "description": "알고리즘 투명성은 알고리즘의 내부 작동 방식과 의사결정 과정을 명확하고 개방적으로 공개하는 것을 의미합니다. 이는 AI와 머신러닝 분야에서 책임감, 신뢰, 법적·윤리적 기준 준수를 보장하는 데 매우 중요합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/algorithmic-transparency/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-211",
    "name": "애니워드",
    "description": "애니워드는 마케팅 팀이 임팩트 있고 브랜드에 맞는 콘텐츠를 생성할 수 있도록 도와주는 AI 기반 카피라이팅 도구입니다. 데이터 기반 인사이트를 활용해 다양한 마케팅 채널에 맞춘 카피를 최적화하여 콘텐츠 제작을 간소화합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/anyword/",
    "category": "비즈니스 AI & 자동화",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-212",
    "name": "앤트로픽의 Claude LLM",
    "description": "앤트로픽의 Claude에 대해 자세히 알아보세요. 사용 목적, 제공되는 다양한 모델, 고유한 기능을 이해할 수 있습니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/claude-llm-by-anthropic/",
    "category": "LLM & 생성형 AI",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-213",
    "name": "양방향 LSTM",
    "description": "양방향 장기 단기 메모리(BiLSTM)는 순차 데이터를 전방향과 역방향 모두에서 처리하여, NLP, 음성 인식, 생물정보학 등에서 맥락적 이해를 향상시키는 고급 순환 신경망(RNN) 아키텍처입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/bidirectional-lstm/",
    "category": "자연어 & 멀티모달",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-214",
    "name": "양자 컴퓨팅",
    "description": "양자 컴퓨팅이 무엇인지 쉽고 간단하게 알아보세요. 어떻게 활용되는지, 어떤 도전과제와 미래의 희망이 있는지 확인할 수 있습니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/quantum-computing/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-215",
    "name": "언더피팅",
    "description": "언더피팅은 머신러닝 모델이 데이터의 근본적인 경향을 포착하기에는 너무 단순할 때 발생합니다. 이로 인해 보이지 않는 데이터와 학습 데이터 모두에서 성능이 저하되며, 이는 주로 모델의 복잡성 부족, 불충분한 학습, 또는 부적절한 피처 선택 때문입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/underfitting/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-216",
    "name": "언어 감지",
    "description": "대형 언어 모델(LLM)에서의 언어 감지는 입력 텍스트의 언어를 식별하여 챗봇, 번역, 콘텐츠 검열 등 다국어 애플리케이션에서 정확한 처리를 가능하게 하는 과정입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/language-detection/",
    "category": "LLM & 생성형 AI",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-217",
    "name": "에이전틱(Agentic)",
    "description": "에이전틱 AI는 시스템이 자율적으로 행동하고, 결정을 내리며, 최소한의 인간 감독으로 복잡한 작업을 수행할 수 있도록 하는 인공지능의 고급 분야입니다. 기존의 AI와 달리, 에이전틱 시스템은 데이터를 분석하고, 역동적인 환경에 적응하며, 다단계 프로세스를 자율적이고 효율적으로 실행합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/agentic/",
    "category": "AI 에이전트 & RAG",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-218",
    "name": "엔터테인먼트 분야의 AI",
    "description": "AI는 엔터테인먼트 산업을 혁신하며, 게임, 영화, 음악 분야에서 역동적인 상호작용, 개인화, 실시간 콘텐츠 진화를 통해 새로운 경험을 제공합니다. AI는 적응형 게임, 지능형 NPC, 맞춤형 사용자 경험을 가능하게 하여 스토리텔링과 몰입 방식을 재구성하고 있습니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/ai-in-entertainment/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-219",
    "name": "역전파(Backpropagation)",
    "description": "역전파는 인공 신경망의 예측 오류를 최소화하기 위해 가중치를 조정하여 학습시키는 알고리즘입니다. 작동 원리, 단계, 신경망 학습에서의 원칙을 알아보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/backpropagation/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-220",
    "name": "연상 기억(Associative Memory)",
    "description": "인공지능(AI)에서의 연상 기억은 시스템이 패턴과 연관성을 바탕으로 정보를 회상할 수 있도록 하여 인간의 기억을 모방합니다. 이 기억 모델은 패턴 인식, 데이터 검색, 그리고 챗봇·자동화 도구 등 AI 애플리케이션에서 학습 능력을 향상시킵니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/associative-memory/",
    "category": "비즈니스 AI & 자동화",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-221",
    "name": "연합 학습",
    "description": "연합 학습은 여러 기기가 학습 데이터를 로컬에 보관한 채로 공동의 모델을 훈련하는 협업형 머신러닝 기법입니다. 이 접근 방식은 프라이버시를 강화하고 지연 시간을 줄이며, 원시 데이터를 공유하지 않고도 수백만 대의 기기에서 확장 가능한 AI를 가능하게 합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/federated-learning/",
    "category": "보안 & 프라이버시",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-222",
    "name": "영업 스크립트 생성기",
    "description": "AI 영업 스크립트 생성기가 NLP와 NLG를 활용해 통화, 이메일, 영상, 소셜 아웃리치에 맞춘 맞춤형·설득력 있는 영업 스크립트를 제작하며, 영업 커뮤니케이션을 간소화하고 전환율을 높이는 방법을 알아보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/sales-script-generator/",
    "category": "자연어 & 멀티모달",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-223",
    "name": "예측 모델링",
    "description": "예측 모델링은 데이터 과학과 통계 분야에서 과거의 데이터 패턴을 분석하여 미래의 결과를 예측하는 정교한 과정입니다. 통계 기법과 머신러닝 알고리즘을 활용하여 금융, 의료, 마케팅 등 다양한 산업에서 트렌드와 행동을 예측하는 모델을 만듭니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/predictive-modeling/",
    "category": "비즈니스 AI & 자동화",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-224",
    "name": "예측 분석",
    "description": "AI 기반 예측 분석 기술, 작동 원리, 그리고 다양한 산업에 미치는 이점에 대해 자세히 알아보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/predictive-analytics/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-225",
    "name": "오디오 전사",
    "description": "오디오 전사는 오디오 녹음에서 말로 된 언어를 문자로 변환하는 과정으로, 연설, 인터뷰, 강의 및 기타 오디오 형식을 접근 가능하고 검색 가능하게 만듭니다. 인공지능(AI)의 발전으로 전사 정확도와 효율성이 향상되어 미디어, 학계, 법률, 콘텐츠 제작 산업을 지원하고 있습니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/audio-transcription/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-226",
    "name": "오픈 뉴럴 네트워크 익스체인지(ONNX)",
    "description": "오픈 뉴럴 네트워크 익스체인지(ONNX)는 다양한 프레임워크 간에 머신러닝 모델을 원활하게 교환할 수 있도록 하는 오픈 소스 포맷으로, 배포의 유연성, 표준화, 하드웨어 최적화를 강화합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/open-neural-network-exchange-onnx/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-227",
    "name": "오픈AI",
    "description": "오픈AI는 GPT, DALL-E, ChatGPT를 개발한 선도적인 인공지능 연구 기관으로, 인류를 위한 안전하고 유익한 범용 인공지능(AGI) 개발을 목표로 하고 있습니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/openai/",
    "category": "보안 & 프라이버시",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-228",
    "name": "온톨로지",
    "description": "인공지능(AI)에서 온톨로지는 지식의 공유된 개념화를 공식적으로 명세한 것으로, 클래스, 속성, 관계를 정의하여 지식을 모델링합니다. 온톨로지는 지식 표현, 데이터 통합, 추론을 향상시켜 NLP, 시맨틱 웹, 전문가 시스템 등 다양한 AI 응용 분야를 지원합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/ontology/",
    "category": "자연어 & 멀티모달",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-229",
    "name": "워드 임베딩",
    "description": "워드 임베딩은 연속적인 벡터 공간에서 단어를 정교하게 표현하여, 의미적·구문적 관계를 포착함으로써 텍스트 분류, 기계 번역, 감정 분석 등 고급 자연어 처리(NLP) 작업에 활용됩니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/word-embeddings/",
    "category": "AI 에이전트 & RAG",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-230",
    "name": "웹사이트 생성기",
    "description": "코드 내보내기 기능이 있는 AI 웹사이트 생성기는 인공지능을 활용해 웹사이트 제작을 자동화하면서, 사용자가 HTML, CSS, JavaScript 또는 인기 프레임워크의 코드로 내보내고 커스터마이즈할 수 있는 소프트웨어 도구입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/website-generator/",
    "category": "비즈니스 AI & 자동화",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-231",
    "name": "윈도잉(Windowing)",
    "description": "인공지능에서 윈도잉(windowing)은 데이터를 세그먼트 또는 “윈도”로 나누어 순차적 정보를 효율적으로 분석하는 방법을 말합니다. NLP와 LLM에서 필수적인 윈도잉은 번역, 챗봇, 시계열 분석과 같은 작업에서 맥락 처리, 자원 사용, 모델 성능을 최적화합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/windowing/",
    "category": "LLM & 생성형 AI",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-232",
    "name": "은닉 마르코프 모델",
    "description": "은닉 마르코프 모델(HMM)은 기저 상태가 관측 불가능한 시스템을 위한 정교한 통계 모델입니다. 음성 인식, 생물정보학, 금융 등에서 널리 사용되며, HMM은 숨겨진 과정을 해석하고 비터비(Viterbi) 및 바움-웰치(Baum-Welch)와 같은 알고리즘으로 구동됩니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/hidden-markov-model/",
    "category": "자연어 & 멀티모달",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-233",
    "name": "음성 인식",
    "description": "음성 인식(ASR, 자동 음성 인식 또는 스피치 투 텍스트로도 알려짐)은 기계와 프로그램이 구어를 해석하여 문자로 전사할 수 있게 해주는 기술입니다. 이 강력한 기능은 개인별 화자를 식별하는 음성 인식(voice recognition)과는 구별됩니다. 음성 인식은 오로지 구어를 문자로 변환하는 데 중점을 둡니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/speech-recognition/",
    "category": "자연어 & 멀티모달",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-234",
    "name": "응용별 집적 회로(ASIC)",
    "description": "응용별 집적 회로(ASIC)는 특정 작업을 위해 설계된 집적 회로(IC)로, 높은 효율성, 낮은 전력 소비, 최적화된 성능을 제공합니다. ASIC는 AI, 자동화, 암호화폐 채굴 등에서 처리 효율성을 위해 필수적입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/application-specific-integrated-circuits-asics/",
    "category": "비즈니스 AI & 자동화",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-235",
    "name": "의료 분야의 인공지능(AI)",
    "description": "의료 분야의 인공지능(AI)은 머신러닝, 자연어 처리(NLP), 딥러닝과 같은 첨단 알고리즘 및 기술을 활용하여 복잡한 의료 데이터를 분석하고, 진단을 향상시키며, 맞춤형 치료를 제공하고, 운영 효율성을 개선하여 환자 케어를 혁신하고 신약 개발을 가속화합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/ai-in-healthcare/",
    "category": "자연어 & 멀티모달",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-236",
    "name": "의미 분석",
    "description": "의미 분석은 텍스트의 의미를 해석하고 도출하는 데 중요한 자연어 처리(NLP) 기술로, 기계가 언어의 맥락, 감정, 뉘앙스를 이해하여 사용자 상호작용과 비즈니스 인사이트를 향상시킬 수 있도록 합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/semantic-analysis/",
    "category": "자연어 & 멀티모달",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-237",
    "name": "의사결정나무",
    "description": "의사결정나무는 입력 데이터에 기반하여 결정을 내리거나 예측을 수행하는 데 사용되는 감독 학습 알고리즘입니다. 트리와 유사한 구조로 시각화되며, 내부 노드는 테스트를, 가지는 결과를, 리프 노드는 클래스 레이블 또는 값을 나타냅니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/decision-tree/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-238",
    "name": "의사소통에서의 바꾸어 말하기(Paraphrasing)",
    "description": "의사소통에서의 바꾸어 말하기는 다른 사람의 메시지를 원래 의미를 유지하면서 자신의 말로 다시 표현하는 능력입니다. 이는 명확성을 보장하고, 이해를 촉진하며, 효율적으로 다양한 표현을 제시하는 AI 도구로 더욱 향상될 수 있습니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/paraphrasing-in-communication/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-239",
    "name": "의인화",
    "description": "의인화는 동물, 식물, 무생물 등 인간이 아닌 존재에 인간의 특성, 감정, 또는 의도를 부여하는 것입니다. 이는 인간의 심리와 문화에 깊이 뿌리내려 있으며, 이야기, 종교, 미디어, 일상생활 등 여러 영역에서 나타나 감정적 연결과 이해를 촉진합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/anthropomorphism/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-240",
    "name": "의존 구문 분석",
    "description": "의존 구문 분석은 NLP에서 단어들 간의 문법적 관계를 식별하여 트리 구조를 형성하는 구문 분석 방법으로, 기계 번역, 감정 분석, 정보 추출 등 다양한 응용 분야에 필수적입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/dependency-parsing/",
    "category": "자연어 & 멀티모달",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-241",
    "name": "이데오그램 AI",
    "description": "이데오그램 AI는 인공지능을 활용해 텍스트 프롬프트를 고품질 이미지로 변환하는 혁신적인 이미지 생성 플랫폼입니다. 딥러닝 신경망을 활용하여 이데오그램은 텍스트와 시각적 요소 간의 연결을 이해함으로써, 사용자가 설명한 내용과 밀접하게 일치하는 이미지를 생성할 수 있도록 합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/ideogram/",
    "category": "LLM & 생성형 AI",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-242",
    "name": "이미지 인식",
    "description": "AI에서 이미지 인식이 무엇인지 알아보세요. 어떤 용도로 사용되는지, 최신 트렌드는 무엇인지, 유사 기술과 어떻게 다른지 설명합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/image-recognition/",
    "category": "자연어 & 멀티모달",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-243",
    "name": "이미지에서의 이상 탐지",
    "description": "이미지에서의 이상 탐지는 정상에서 벗어난 패턴을 식별하여 산업 검사나 의료 영상과 같은 분야에서 중요하게 사용됩니다. 비지도 및 약지도 방법, AI 통합, 실제 활용 사례에 대해 알아보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/anomaly-detection-in-images/",
    "category": "자연어 & 멀티모달",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-244",
    "name": "이상 탐지",
    "description": "이상 탐지는 데이터셋 내에서 기대되는 기준에서 벗어나는 데이터 포인트, 이벤트 또는 패턴을 식별하는 과정으로, 인공지능(AI)과 머신러닝을 활용하여 사이버보안, 금융, 의료 등 다양한 산업에서 실시간 자동 탐지를 구현합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/anomaly-detection/",
    "category": "보안 & 프라이버시",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-245",
    "name": "이형이의어",
    "description": "이형이의어란 무엇인가요? 이형이의어는 두 개 이상의 단어가 동일한 철자를 가지지만 발음과 의미가 서로 다른 독특한 언어 현상입니다. 이러한 단어들은 동철이의어이지만 동음이의어는 아닙니다. 즉, 이형이의어는 문자상으로는 같아 보이지만 발음이 다르고, 맥락에 따라 서로 다른 의미를 전달합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/heteronym/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-246",
    "name": "인간 피드백 기반 강화 학습(RLHF)",
    "description": "인간 피드백 기반 강화 학습(RLHF)은 강화 학습 알고리즘의 훈련 과정에 인간의 입력을 통합하여 AI가 보다 인간의 가치와 선호도에 맞추도록 유도하는 기계 학습 기법입니다. 기존의 강화 학습이 미리 정의된 보상 신호에만 의존하는 것과 달리, RLHF는 인간의 판단을 활용하여 AI 모델의 행동을 조정하고 개선합니다. 이 접근 방식은 AI가 인간의 가치와 선호에 더 밀접하게 맞춰지도록 하여, 복잡하고 주관적인 과제에서 특히 유용합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/reinforcement-learning-from-human-feedback-rlhf/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-247",
    "name": "인공 신경망 (ANNs)",
    "description": "인공 신경망(ANNs)은 인간 두뇌를 본떠 만든 기계 학습 알고리즘의 한 종류입니다. 이 계산 모델은 서로 연결된 노드 또는 '뉴런'들로 구성되어 복잡한 문제를 함께 해결합니다. ANNs는 이미지 및 음성 인식, 자연어 처리, 예측 분석 등 다양한 분야에서 널리 사용됩니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/artificial-neural-networks-anns/",
    "category": "자연어 & 멀티모달",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-248",
    "name": "인공지능 초지능(ASI)",
    "description": "인공지능 초지능(ASI)은 모든 영역에서 인간 지능을 능가하는 이론적 AI로, 자기 개선과 다중 모달 능력을 갖추고 있습니다. 그 특징, 구성 요소, 응용 분야, 이점, 윤리적 위험성에 대해 알아보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/artificial-superintelligence-asi/",
    "category": "보안 & 프라이버시",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-249",
    "name": "인공지능 투자 수익률(ROAI)",
    "description": "인공지능 투자 수익률(ROAI)은 AI 투자가 기업의 운영, 생산성, 수익성에 미치는 영향을 측정합니다. 전략, 실무 사례, 연구 인사이트를 통해 AI 프로젝트의 수익을 평가, 측정, 극대화하는 방법을 알아보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/return-on-artificial-intelligence-roai/",
    "category": "비즈니스 AI & 자동화",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-250",
    "name": "인과 추론",
    "description": "인과 추론은 변수 간의 인과관계를 규명하기 위해 사용되는 방법론적 접근법으로, 상관관계를 넘어선 인과 메커니즘을 이해하고 교란 변수와 같은 과제를 해결하는 데 과학 분야에서 매우 중요합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/causal-inference/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-251",
    "name": "인사이트 엔진",
    "description": "인사이트 엔진이란 무엇인지 알아보세요—AI 기반의 고급 플랫폼으로, 컨텍스트와 의도를 이해하여 데이터 검색과 분석을 향상시킵니다. 인사이트 엔진이 자연어 처리(NLP), 머신러닝, 딥러닝을 어떻게 통합해 구조화 및 비구조화 데이터 소스에서 실행 가능한 인사이트를 제공하는지 확인하세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/insight-engine/",
    "category": "자연어 & 멀티모달",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-252",
    "name": "인스턴스 분할",
    "description": "인스턴스 분할은 이미지 내의 각 개별 객체를 픽셀 단위로 감지하고 윤곽을 그리는 컴퓨터 비전 작업입니다. 이는 객체 감지나 의미론적 분할보다 더 상세한 이해를 제공하여 의료 영상, 자율주행, 로보틱스와 같은 분야에서 매우 중요합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/instance-segmentation/",
    "category": "자연어 & 멀티모달",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-253",
    "name": "인스트럭션 튜닝",
    "description": "인스트럭션 튜닝은 인공지능(AI) 분야에서 대형 언어 모델(LLM)을 인스트럭션-응답 쌍 데이터로 미세 조정하여, 인간의 지시를 따르고 특정 작업을 수행하는 능력을 향상시키는 기법입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/instruction-tuning/",
    "category": "LLM & 생성형 AI",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-254",
    "name": "인지 지도",
    "description": "인지 지도는 공간적 관계와 환경에 대한 정신적 표상으로, 개인이 주변 위치와 속성에 대한 정보를 습득, 저장, 회상, 해독할 수 있게 해줍니다. 이는 탐색, 학습, 기억의 근간이 되며, AI와 로봇공학 분야에서도 점점 더 큰 영향을 미치고 있습니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/cognitive-map/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-255",
    "name": "인지 컴퓨팅",
    "description": "인지 컴퓨팅은 복잡한 상황에서 인간의 사고 과정을 모방하는 혁신적인 기술 모델입니다. 인공지능(AI)과 신호 처리를 통합해 인간의 인지를 재현하고, 방대한 구조화·비구조화 데이터를 처리하여 의사결정을 향상시킵니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/cognitive-computing/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-256",
    "name": "일반화 오류",
    "description": "일반화 오류는 머신러닝 모델이 보지 않은 데이터를 얼마나 잘 예측하는지 측정하며, 편향과 분산의 균형을 맞춰 견고하고 신뢰할 수 있는 AI 응용을 보장합니다. 그 중요성과 수학적 정의, 실제 성공을 위한 효과적인 최소화 기법을 알아보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/generalization-error/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-257",
    "name": "읽기 수준",
    "description": "읽기 수준이란 무엇이며, 어떻게 측정되고 왜 중요한지 알아보세요. 다양한 평가 시스템, 읽기 능력에 영향을 주는 요인, 읽기 수준을 높이기 위한 전략과 AI가 개인 맞춤형 학습에서 어떤 역할을 하는지도 함께 학습할 수 있습니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/reading-level/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-258",
    "name": "임베딩 벡터",
    "description": "임베딩 벡터는 데이터의 의미적 및 맥락적 관계를 포착하는 다차원 공간에서의 밀집 수치 표현입니다. 임베딩 벡터가 자연어 처리, 이미지 처리, 추천 등 다양한 AI 작업을 어떻게 지원하는지 알아보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/embedding-vector/",
    "category": "AI 에이전트 & RAG",
    "initial": "ㅇ"
  },
  {
    "id": "glossary-259",
    "name": "자동 분류",
    "description": "자동 분류는 머신러닝, 자연어 처리(NLP), 시맨틱 분석과 같은 기술을 활용해 속성을 분석하고 태그를 할당함으로써 콘텐츠 분류를 자동화합니다. 이는 다양한 산업에서 효율성, 검색성, 데이터 거버넌스를 향상시킵니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/auto-classification/",
    "category": "자연어 & 멀티모달",
    "initial": "ㅈ"
  },
  {
    "id": "glossary-260",
    "name": "자랑 북(Brag Book)",
    "description": "자랑 북(Brag Book)은 개인의 전문적인 성과, 수상 내역, 그리고 자신의 역량과 업적을 입증할 수 있는 구체적인 증거들을 모아 놓은 자료집입니다. 이는 자신의 전문성을 보여주고, 경력 발전을 추적하며, 직장 내에서 자신의 가치를 확실하게 증명할 수 있는 강력한 도구로 사용됩니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/brag-book/",
    "category": "AI 에이전트 & RAG",
    "initial": "ㅈ"
  },
  {
    "id": "glossary-261",
    "name": "자연어 생성(NLG)",
    "description": "자연어 생성(NLG)은 구조화된 데이터를 인간과 유사한 텍스트로 변환하는 데 중점을 둔 AI의 하위 분야입니다. NLG는 챗봇, 음성 비서, 콘텐츠 생성 등에서 일관되고 맥락에 맞으며 문법적으로 올바른 내러티브를 생성함으로써 다양한 애플리케이션에 활용됩니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/natural-language-generation-nlg/",
    "category": "자연어 & 멀티모달",
    "initial": "ㅈ"
  },
  {
    "id": "glossary-262",
    "name": "자연어 이해 (NLU)",
    "description": "자연어 이해(NLU)는 AI의 하위 분야로, 기계가 인간의 언어를 맥락적으로 이해하고 해석할 수 있도록 하여, 기본적인 텍스트 처리 수준을 넘어 의도, 의미, 뉘앙스를 인식해 챗봇, 감정 분석, 기계 번역과 같은 다양한 응용 분야에 활용됩니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/natural-language-understanding-nlu/",
    "category": "자연어 & 멀티모달",
    "initial": "ㅈ"
  },
  {
    "id": "glossary-263",
    "name": "자연어 처리(NLP)",
    "description": "자연어 처리(NLP)는 인공지능(AI)의 한 분야로, 컴퓨터가 인간의 언어를 이해하고 해석하며 생성할 수 있도록 합니다. 주요 개념, 작동 방식, 산업별 응용 사례를 알아보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/natural-language-processing-nlp/",
    "category": "자연어 & 멀티모달",
    "initial": "ㅈ"
  },
  {
    "id": "glossary-264",
    "name": "자율주행 차량",
    "description": "AI, 센서, 연결성을 활용하여 인간의 개입 없이 작동하는 자율주행 차량(무인 자동차)에 대해 알아보세요. 핵심 기술, AI의 역할, LLM 통합, 도전 과제, 그리고 스마트 교통의 미래를 살펴봅니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/autonomous-vehicles/",
    "category": "LLM & 생성형 AI",
    "initial": "ㅈ"
  },
  {
    "id": "glossary-265",
    "name": "장기 단기 메모리(LSTM)",
    "description": "장기 단기 메모리(Long Short-Term Memory, LSTM)는 순차 데이터의 장기 의존성을 학습하도록 설계된 특수한 종류의 순환 신경망(RNN) 아키텍처입니다. LSTM 네트워크는 메모리 셀과 게이팅 메커니즘을 활용하여 기울기 소실 문제를 해결하므로, 언어 모델링, 음성 인식, 시계열 예측 등의 작업에 필수적입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/long-short-term-memory-lstm/",
    "category": "LLM & 생성형 AI",
    "initial": "ㅈ"
  },
  {
    "id": "glossary-266",
    "name": "장면 텍스트 인식 (STR)",
    "description": "장면 텍스트 인식(STR)은 광학 문자 인식(OCR)의 한 분야로, AI와 딥러닝 모델을 활용하여 자연 장면에서 촬영된 이미지 속 텍스트를 식별하고 해석하는 데 중점을 둡니다. STR은 복잡한 현실 세계의 텍스트를 기계가 읽을 수 있는 형식으로 변환하여 자율주행차, 증강현실, 스마트 시티 인프라 등 다양한 분야의 응용 프로그램을 지원합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/scene-text-recognition-str/",
    "category": "자연어 & 멀티모달",
    "initial": "ㅈ"
  },
  {
    "id": "glossary-267",
    "name": "재귀 프롬프트(Recursive Prompting)",
    "description": "재귀 프롬프트는 GPT-4와 같은 대형 언어 모델에서 사용되는 AI 기술로, 사용자와의 반복적인 대화 과정을 통해 출력 결과를 점진적으로 개선하여 더 높은 품질과 정확한 결과를 도출할 수 있도록 합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/recursive-prompting/",
    "category": "LLM & 생성형 AI",
    "initial": "ㅈ"
  },
  {
    "id": "glossary-268",
    "name": "적응형 학습",
    "description": "적응형 학습은 기술을 활용하여 각 학생에게 맞춤화된 학습 경험을 제공하는 혁신적인 교육 방법입니다. AI, 머신러닝, 데이터 분석을 통해 적응형 학습은 개인의 필요에 맞춘 맞춤형 교육 콘텐츠를 제공합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/adaptive-learning/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅈ"
  },
  {
    "id": "glossary-269",
    "name": "전문가 시스템",
    "description": "AI 전문가 시스템은 인간 전문가와 유사하게 복잡한 문제를 해결하고 의사결정을 내리도록 설계된 고급 컴퓨터 프로그램입니다. 이러한 시스템은 방대한 지식 기반과 추론 규칙을 활용하여 데이터를 처리하고 해결책이나 권장 사항을 제공합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/expert-system/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅈ"
  },
  {
    "id": "glossary-270",
    "name": "전이 학습",
    "description": "전이 학습은 한 작업에 대해 학습된 모델을 관련된 다른 작업에 재사용할 수 있게 하는 고급 머신러닝 기법으로, 특히 데이터가 부족할 때 효율성과 성능을 향상시킵니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/transfer-learning-2/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅈ"
  },
  {
    "id": "glossary-271",
    "name": "정규화(Regularization)",
    "description": "인공지능(AI)에서 정규화는 머신러닝 모델의 학습 과정에 제약을 도입해 과적합을 방지하고, 보지 못한 데이터에 더 잘 일반화할 수 있도록 하는 일련의 기법을 의미합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/regularization/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅈ"
  },
  {
    "id": "glossary-272",
    "name": "정보 검색",
    "description": "정보 검색은 AI, 자연어 처리(NLP), 그리고 기계 학습을 활용하여 사용자의 요구를 충족하는 데이터를 효율적이고 정확하게 검색합니다. 웹 검색 엔진, 디지털 도서관, 엔터프라이즈 솔루션의 기반이 되는 IR은 모호성, 알고리즘 편향, 확장성 등 다양한 과제를 해결하며, 미래에는 생성형 AI와 딥러닝을 중심으로 발전할 전망입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/information-retrieval/",
    "category": "LLM & 생성형 AI",
    "initial": "ㅈ"
  },
  {
    "id": "glossary-273",
    "name": "제로-샷 러닝",
    "description": "제로-샷 러닝은 AI에서 모델이 명시적으로 학습하지 않은 객체나 데이터 카테고리를 의미적 설명이나 속성을 활용해 추론함으로써 인식하는 방법입니다. 학습 데이터를 수집하기 어렵거나 불가능할 때 특히 유용합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/zero-shot-learning/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅈ"
  },
  {
    "id": "glossary-274",
    "name": "제조업의 AI",
    "description": "제조업에서의 인공지능(AI)은 생산성을 높이고 효율성과 의사결정을 향상시키기 위해 첨단 기술을 통합하여 생산 현장을 혁신하고 있습니다. AI는 복잡한 작업을 자동화하고, 정밀도를 개선하며, 워크플로우를 최적화하여 혁신과 운영 우수성을 이끕니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/ai-in-manufacturing/",
    "category": "AI 에이전트 & RAG",
    "initial": "ㅈ"
  },
  {
    "id": "glossary-275",
    "name": "주피터 노트북",
    "description": "주피터 노트북은 사용자가 실시간 코드, 수식, 시각화, 설명 텍스트가 포함된 문서를 생성하고 공유할 수 있게 해주는 오픈 소스 웹 애플리케이션입니다. 데이터 과학, 머신러닝, 교육, 연구 분야에서 널리 사용되며, 40개 이상의 프로그래밍 언어와 AI 도구와의 완벽한 통합을 지원합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/jupyter-notebook/",
    "category": "자연어 & 멀티모달",
    "initial": "ㅈ"
  },
  {
    "id": "glossary-276",
    "name": "준지도 학습",
    "description": "준지도 학습(SSL)은 라벨이 지정된 데이터와 라벨이 없는 데이터를 모두 활용하여 모델을 학습시키는 머신러닝 기법입니다. 모든 데이터에 라벨을 지정하는 것이 비현실적이거나 비용이 많이 드는 경우에 이상적입니다. 감독 학습과 비감독 학습의 장점을 결합하여 정확도와 일반화 성능을 향상시킵니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/semi-supervised-learning/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅈ"
  },
  {
    "id": "glossary-277",
    "name": "지능형 문서 처리(IDP)",
    "description": "지능형 문서 처리(IDP)는 AI를 활용하여 다양한 문서에서 데이터 추출, 처리, 분석을 자동화하는 첨단 기술입니다. 비정형 및 반정형 데이터를 처리하고, 워크플로우를 간소화하며, 산업 전반에 걸쳐 비즈니스 효율성을 높입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/intelligent-document-processing-idp/",
    "category": "AI 에이전트 & RAG",
    "initial": "ㅈ"
  },
  {
    "id": "glossary-278",
    "name": "지능형 에이전트",
    "description": "지능형 에이전트는 센서를 통해 환경을 인지하고, 액추에이터를 사용하여 그 환경에 작용하는 자율적인 존재로, 인공지능 기능을 갖추어 의사결정 및 문제 해결을 수행합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/intelligent-agents/",
    "category": "AI 에이전트 & RAG",
    "initial": "ㅈ"
  },
  {
    "id": "glossary-279",
    "name": "지도 학습",
    "description": "지도 학습은 알고리즘이 레이블이 지정된 데이터를 기반으로 학습하여 새로운, 보지 못한 데이터에 대해 정확한 예측이나 분류를 할 수 있도록 하는 인공지능 및 머신러닝의 기본 개념입니다. 주요 구성 요소, 종류, 그리고 장점에 대해 알아보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/supervised-learning/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅈ"
  },
  {
    "id": "glossary-280",
    "name": "지식 공학",
    "description": "AI에서 지식 공학은 의료 진단, 금융 분석, 기술적 문제 해결 등과 같은 분야에서 인간 전문가의 전문성을 모방하여 복잡한 문제를 해결하기 위해 지식을 활용하는 지능형 시스템을 구축하는 과정입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/knowledge-engineering/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅈ"
  },
  {
    "id": "glossary-281",
    "name": "지식 컷오프 날짜",
    "description": "지식 컷오프 날짜는 AI 모델이 더 이상 최신 정보를 반영하지 않는 특정 시점을 의미합니다. 이러한 날짜가 왜 중요한지, AI 모델에 어떤 영향을 미치는지, 그리고 GPT-3.5, Bard, Claude 등 주요 모델들의 컷오프 날짜를 확인하세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/cutoff-date/",
    "category": "LLM & 생성형 AI",
    "initial": "ㅈ"
  },
  {
    "id": "glossary-282",
    "name": "질문 응답",
    "description": "검색 기반 생성(RAG)을 활용한 질문 응답은 정보 검색과 자연어 생성을 결합하여, 외부 소스의 관련성 있고 최신 데이터를 활용해 대형 언어 모델(LLM)의 답변을 보완합니다. 이 하이브리드 접근 방식은 정확성, 관련성, 그리고 변화하는 환경에 대한 적응력을 개선합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/question-answering/",
    "category": "AI 에이전트 & RAG",
    "initial": "ㅈ"
  },
  {
    "id": "glossary-283",
    "name": "차별",
    "description": "AI에서의 차별은 인종, 성별, 나이, 장애와 같은 보호 특성에 기반하여 개인이나 집단을 불공정하거나 불평등하게 대우하는 것을 의미합니다. 이는 주로 데이터 수집, 알고리즘 개발, 배포 과정에서 AI 시스템에 내재된 편향에서 비롯되며, 사회적·경제적 평등에 큰 영향을 미칠 수 있습니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/discrimination/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅊ"
  },
  {
    "id": "glossary-284",
    "name": "차원 축소",
    "description": "차원 축소는 데이터 처리와 머신러닝에서 핵심적인 기법으로, 데이터셋의 입력 변수 개수를 줄이면서도 필수 정보를 보존하여 모델을 단순화하고 성능을 향상시킵니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/dimensionality-reduction/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅊ"
  },
  {
    "id": "glossary-285",
    "name": "창발성",
    "description": "AI에서의 창발성은 시스템의 구성 요소들 간의 상호작용에서 발생하는, 명시적으로 프로그래밍되지 않은 정교하고 시스템 전체에 걸친 패턴과 행동을 의미합니다. 이러한 창발적 행동은 예측 가능성과 윤리적 문제를 야기하며, 그 영향을 관리하기 위한 안전장치와 지침이 필요합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/emergence/",
    "category": "보안 & 프라이버시",
    "initial": "ㅊ"
  },
  {
    "id": "glossary-286",
    "name": "챗GPT",
    "description": "챗GPT는 OpenAI에서 개발한 최첨단 AI 챗봇으로, 고급 자연어 처리(NLP)를 활용해 인간과 유사한 대화를 가능하게 하고, 질문 답변부터 콘텐츠 생성에 이르기까지 다양한 작업을 지원합니다. 2022년에 출시된 이후, 콘텐츠 제작, 코딩, 고객 지원 등 여러 산업 분야에서 널리 사용되고 있습니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/chatgpt/",
    "category": "LLM & 생성형 AI",
    "initial": "ㅊ"
  },
  {
    "id": "glossary-287",
    "name": "챗봇",
    "description": "챗봇은 AI와 자연어 처리를 활용해 인간과의 대화를 모방하는 디지털 도구로, 24시간 지원, 확장성, 비용 효율성을 제공합니다. 챗봇의 작동 방식, 유형, 이점, 그리고 FlowHunt와 함께하는 실제 적용 사례를 알아보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/chatbot/",
    "category": "자연어 & 멀티모달",
    "initial": "ㅊ"
  },
  {
    "id": "glossary-288",
    "name": "추출형 AI",
    "description": "추출형 AI는 기존 데이터 소스에서 특정 정보를 식별하고 추출하는 데 중점을 둔 인공지능의 전문 분야입니다. 생성형 AI와 달리, 추출형 AI는 고급 자연어 처리(NLP) 기술을 활용하여 구조화된 또는 비구조화된 데이터셋에서 정확한 데이터를 찾아내어 데이터 추출과 정보 검색에서 높은 정확성과 신뢰성을 보장합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/extractive-ai/",
    "category": "LLM & 생성형 AI",
    "initial": "ㅊ"
  },
  {
    "id": "glossary-289",
    "name": "카피 에디팅",
    "description": "카피 에디팅은 작성된 자료를 검토하고 수정하여 정확성, 가독성, 일관성을 높이는 과정입니다. 문법 오류, 맞춤법 실수, 구두점 문제를 확인하고, 문서 전반에 걸쳐 스타일과 톤의 일관성을 유지하는 것이 포함됩니다. Grammarly와 같은 AI 도구가 일상적인 검사를 도와주지만, 인간의 판단이 여전히 중요합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/copy-editing/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅋ"
  },
  {
    "id": "glossary-290",
    "name": "캐글(Kaggle)",
    "description": "캐글(Kaggle)은 데이터 과학자와 머신러닝 엔지니어들이 협업하고, 학습하며, 대회에 참가하고, 인사이트를 공유할 수 있는 온라인 커뮤니티 및 플랫폼입니다. 2017년 구글에 인수된 이후, 캐글은 경진대회, 데이터셋, 노트북, 교육 자료의 허브로서 인공지능 분야의 혁신과 역량 개발을 촉진하고 있습니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/kaggle/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅋ"
  },
  {
    "id": "glossary-291",
    "name": "캐시 증강 생성(CAG)",
    "description": "캐시 증강 생성(CAG)은 대규모 언어 모델(LLM)의 성능을 향상시키기 위해 지식을 미리 계산된 키-값 캐시로 사전 로드하여, 정적 지식 작업에 대해 저지연, 정확하고 효율적인 AI 성능을 가능하게 하는 혁신적인 접근 방식입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/cache-augmented-generation-cag/",
    "category": "LLM & 생성형 AI",
    "initial": "ㅋ"
  },
  {
    "id": "glossary-292",
    "name": "컴퓨터 비전",
    "description": "컴퓨터 비전은 인공지능(AI) 분야 중 하나로, 컴퓨터가 시각적 세계를 해석하고 이해하도록 하는 데 중점을 둔 학문입니다. 카메라, 비디오, 그리고 딥러닝 모델에서 얻은 디지털 이미지를 활용해 기계는 물체를 정확하게 식별 및 분류하고, 보고 있는 것에 반응할 수 있습니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/computer-vision/",
    "category": "자연어 & 멀티모달",
    "initial": "ㅋ"
  },
  {
    "id": "glossary-293",
    "name": "컴플라이언스 보고",
    "description": "컴플라이언스 보고는 조직이 내부 정책, 업계 표준, 규제 요건 준수 증거를 문서화하고 제시할 수 있도록 하는 구조적이고 체계적인 프로세스입니다. 이는 위험 관리, 투명성, 법적 보호를 다양한 산업 분야에서 보장합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/compliance-reporting/",
    "category": "보안 & 프라이버시",
    "initial": "ㅋ"
  },
  {
    "id": "glossary-294",
    "name": "케라스",
    "description": "케라스는 강력하고 사용하기 쉬운 오픈소스 고수준 신경망 API로, 파이썬으로 작성되었으며 TensorFlow, CNTK 또는 Theano 위에서 실행할 수 있습니다. 빠른 실험을 가능하게 하며, 모듈성과 단순성으로 프로덕션과 연구 모두에서 사용할 수 있습니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/keras/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅋ"
  },
  {
    "id": "glossary-295",
    "name": "코퍼스",
    "description": "AI에서 코퍼스(복수형: 코퍼라)는 AI 모델을 훈련하고 평가하는 데 사용되는 대규모의 구조화된 텍스트 또는 오디오 데이터 집합을 의미합니다. 코퍼라는 AI 시스템이 인간 언어를 이해, 해석, 생성하는 방법을 학습하는 데 필수적입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/corpus/",
    "category": "자연어 & 멀티모달",
    "initial": "ㅋ"
  },
  {
    "id": "glossary-296",
    "name": "콘텐츠 강화",
    "description": "AI를 활용한 콘텐츠 강화는 원시적이고 비정형적인 콘텐츠에 인공지능 기술을 적용하여 의미 있는 정보, 구조, 인사이트를 추출함으로써 데이터 분석, 정보 검색, 의사결정 등 다양한 활용을 위해 콘텐츠를 더욱 접근하기 쉽고, 검색 가능하며, 가치 있게 만듭니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/content-enrichment/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅋ"
  },
  {
    "id": "glossary-297",
    "name": "쿠브플로우",
    "description": "쿠브플로우(Kubeflow)는 오픈소스 머신러닝(ML) 플랫폼으로, 쿠버네티스 위에서 ML 워크플로우의 배포, 관리 및 확장을 간소화합니다. 모델 개발부터 배포 및 모니터링까지 ML 라이프사이클 전체를 아우르는 다양한 도구를 제공하여 확장성, 재현성 및 자원 활용도를 높여줍니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/kubeflow/",
    "category": "AI 에이전트 & RAG",
    "initial": "ㅋ"
  },
  {
    "id": "glossary-298",
    "name": "쿼리 확장",
    "description": "쿼리 확장은 사용자의 원래 쿼리에 용어나 맥락을 추가하여 문서 검색을 개선하고, 특히 RAG(검색 증강 생성) 시스템에서 더 정확하고 상황에 맞는 응답을 제공하는 과정입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/query-expansion/",
    "category": "AI 에이전트 & RAG",
    "initial": "ㅋ"
  },
  {
    "id": "glossary-299",
    "name": "크로스 엔트로피",
    "description": "크로스 엔트로피는 정보 이론과 머신러닝 모두에서 핵심적인 개념으로, 두 확률 분포 간의 차이를 측정하는 지표입니다. 머신러닝에서는 예측 결과와 실제 레이블 간의 불일치를 정량화하는 손실 함수로 사용되며, 특히 분류 작업에서 모델 성능을 최적화하는 데 중요한 역할을 합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/cross-entropy/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅋ"
  },
  {
    "id": "glossary-300",
    "name": "클로드 오푸스",
    "description": "Anthropic의 클로드 오푸스 모델에 대해 자세히 알아보세요. 강점과 약점, 그리고 다른 모델과의 비교를 확인할 수 있습니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/claude-opus/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅋ"
  },
  {
    "id": "glossary-301",
    "name": "클로드 하이쿠",
    "description": "Anthropic의 가장 빠르고 저렴한 AI 모델인 Claude Haiku에 대해 자세히 알아보세요. 주요 기능, 엔터프라이즈 활용 사례, Claude 3 패밀리 내 다른 모델과의 비교를 확인할 수 있습니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/claude-haiku/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅋ"
  },
  {
    "id": "glossary-302",
    "name": "탐색적 데이터 분석 (EDA)",
    "description": "탐색적 데이터 분석(EDA)은 시각적 방법을 활용하여 데이터셋의 특성을 요약하고, 패턴을 발견하며, 이상치를 탐지하고, 데이터 정제, 모델 선택, 분석을 안내하는 과정입니다. Python, R, Tableau와 같은 도구를 사용합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/exploratory-data-analysis-eda/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅌ"
  },
  {
    "id": "glossary-303",
    "name": "텍스트 분류",
    "description": "텍스트 분류는 텍스트 분류화 또는 텍스트 태깅이라고도 하며, 미리 정의된 범주를 텍스트 문서에 할당하는 핵심 NLP 작업입니다. 이는 분석을 위해 비정형 데이터를 조직하고 구조화하며, 기계 학습 모델을 사용해 감정 분석, 스팸 탐지, 주제 분류와 같은 프로세스를 자동화합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/text-classification/",
    "category": "자연어 & 멀티모달",
    "initial": "ㅌ"
  },
  {
    "id": "glossary-304",
    "name": "텍스트 생성",
    "description": "대형 언어 모델(LLM)을 활용한 텍스트 생성은 머신러닝 모델을 이용해 프롬프트로부터 인간과 유사한 텍스트를 만들어내는 고급 기술을 의미합니다. 트랜스포머 아키텍처로 구동되는 LLM이 콘텐츠 제작, 챗봇, 번역 등 다양한 분야에서 어떻게 혁신을 이끌고 있는지 알아보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/text-generation/",
    "category": "LLM & 생성형 AI",
    "initial": "ㅌ"
  },
  {
    "id": "glossary-305",
    "name": "텍스트 요약",
    "description": "텍스트 요약은 방대한 문서를 간결한 요약으로 정제하여 핵심 정보와 의미를 보존하는 필수적인 AI 프로세스입니다. GPT-4, BERT와 같은 대형 언어 모델을 활용해 추상적, 추출적, 혼합적 방법을 통해 방대한 디지털 콘텐츠를 효율적으로 관리하고 이해할 수 있습니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/text-summarization/",
    "category": "LLM & 생성형 AI",
    "initial": "ㅌ"
  },
  {
    "id": "glossary-306",
    "name": "텍스트 음성 변환(TTS)",
    "description": "텍스트 음성 변환(TTS) 기술은 AI를 활용한 자연스러운 음성으로, 작성된 텍스트를 들을 수 있는 음성으로 변환하는 정교한 소프트웨어 메커니즘입니다. 고객 서비스, 교육, 보조 기술 등 다양한 분야에서 접근성과 사용자 경험을 향상시킵니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/text-to-speech-tts/",
    "category": "자연어 & 멀티모달",
    "initial": "ㅌ"
  },
  {
    "id": "glossary-307",
    "name": "텐서플로우",
    "description": "TensorFlow는 Google Brain 팀이 개발한 오픈소스 라이브러리로, 수치 연산과 대규모 머신러닝을 위해 설계되었습니다. 딥러닝, 신경망을 지원하며 CPU, GPU, TPU에서 구동되어 데이터 수집, 모델 학습, 배포를 간소화합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/tensorflow/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅌ"
  },
  {
    "id": "glossary-308",
    "name": "토큰",
    "description": "대형 언어 모델(LLM)에서 토큰은 모델이 효율적으로 처리하기 위해 숫자 표현으로 변환하는 문자 시퀀스입니다. 토큰은 GPT-3, ChatGPT와 같은 LLM이 언어를 이해하고 생성하는 데 사용하는 텍스트의 기본 단위입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/token/",
    "category": "LLM & 생성형 AI",
    "initial": "ㅌ"
  },
  {
    "id": "glossary-309",
    "name": "튜링 테스트",
    "description": "튜링 테스트는 인공지능(AI) 분야에서 기계가 인간과 구별할 수 없는 지능적 행동을 보일 수 있는지 평가하기 위해 고안된 개념입니다. 1950년 앨런 튜링에 의해 제안된 이 테스트는 인간과 기계가 대화를 나누고, 심판이 어느 쪽이 인간인지 구별하지 못할 경우 기계가 인간처럼 행동한다고 간주합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/turing-test-2/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅌ"
  },
  {
    "id": "glossary-310",
    "name": "트랜스포머",
    "description": "트랜스포머 모델은 텍스트, 음성, 시계열 데이터와 같은 순차 데이터를 처리하도록 특별히 설계된 신경망입니다. 기존의 RNN, CNN과 달리 트랜스포머는 어텐션 메커니즘을 활용하여 입력 시퀀스의 요소별 중요도를 가중치로 반영하며, 이를 통해 NLP, 음성 인식, 유전체학 등 다양한 분야에서 강력한 성능을 보여줍니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/transformer/",
    "category": "자연어 & 멀티모달",
    "initial": "ㅌ"
  },
  {
    "id": "glossary-311",
    "name": "트루스파인더",
    "description": "트루스파인더는 미국의 공개 기록에 대한 접근을 제공하는 온라인 플랫폼으로, 배경 조사, 사람 검색, 상세 보고서를 위해 AI를 활용하여 데이터를 집계합니다. 개인정보 보호와 윤리적 사용을 강조하며, FCRA를 준수하지 않습니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/truthfinder/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅌ"
  },
  {
    "id": "glossary-312",
    "name": "특이점",
    "description": "인공지능에서의 특이점(Singularity)은 기계 지능이 인간 지능을 능가하여 사회에 급격하고 예측 불가능한 변화를 불러올 것으로 예측되는 이론적 미래 시점을 의미합니다. 그 기원, 핵심 개념, 영향, 그리고 계속되는 논쟁을 살펴보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/singularity/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅌ"
  },
  {
    "id": "glossary-313",
    "name": "특징 엔지니어링 및 추출",
    "description": "특징 엔지니어링과 추출이 원시 데이터를 가치 있는 인사이트로 변환하여 AI 모델의 성능을 어떻게 향상시키는지 알아보세요. 특징 생성, 변환, PCA, 오토인코더 등 주요 기법을 통해 ML 모델의 정확성과 효율성을 높이는 방법을 소개합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/feature-engineering-and-extraction/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅌ"
  },
  {
    "id": "glossary-314",
    "name": "특징 추출",
    "description": "특징 추출은 원시 데이터를 정보가 풍부한 특징의 축소된 집합으로 변환하여, 데이터 단순화, 모델 성능 향상, 연산 비용 절감 등 머신러닝을 강화합니다. 이 포괄적인 가이드에서 기법, 응용, 도구, 과학적 통찰을 알아보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/feature-extraction/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅌ"
  },
  {
    "id": "glossary-315",
    "name": "파운데이션 모델",
    "description": "파운데이션 AI 모델은 방대한 데이터로 학습된 대규모 머신러닝 모델로, 다양한 작업에 적응이 가능합니다. 파운데이션 모델은 NLP, 컴퓨터 비전 등 각 분야의 특화 AI 애플리케이션 개발을 위한 다재다능한 기반이 되어 AI 분야에 혁신을 가져왔습니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/foundation-model/",
    "category": "자연어 & 멀티모달",
    "initial": "ㅍ"
  },
  {
    "id": "glossary-316",
    "name": "파이토치",
    "description": "파이토치는 Meta AI에서 개발한 오픈 소스 머신러닝 프레임워크로, 유연성, 동적 계산 그래프, GPU 가속, 그리고 파이썬과의 매끄러운 통합으로 유명합니다. 딥러닝, 컴퓨터 비전, 자연어 처리(NLP), 연구 등 다양한 분야에서 널리 사용되고 있습니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/pytorch/",
    "category": "자연어 & 멀티모달",
    "initial": "ㅍ"
  },
  {
    "id": "glossary-317",
    "name": "파인튜닝(Fine-Tuning)",
    "description": "모델 파인튜닝은 사전 학습된 모델을 새로운 작업에 맞게 소폭 조정하여 데이터와 리소스 요구를 줄입니다. 파인튜닝이 전이 학습을 어떻게 활용하는지, 다양한 기법, 모범 사례, 평가 지표를 통해 NLP, 컴퓨터 비전 등에서 모델 성능을 효율적으로 향상하는 방법을 알아보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/fine-tuning/",
    "category": "LLM & 생성형 AI",
    "initial": "ㅍ"
  },
  {
    "id": "glossary-318",
    "name": "판다스",
    "description": "판다스는 파이썬을 위한 오픈소스 데이터 조작 및 분석 라이브러리로, 그 다양성, 강력한 데이터 구조, 복잡한 데이터셋을 손쉽게 다룰 수 있는 사용 편의성으로 잘 알려져 있습니다. 데이터 분석가와 데이터 과학자를 위한 핵심 도구로, 효율적인 데이터 정제, 변환, 분석을 지원합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/pandas/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅍ"
  },
  {
    "id": "glossary-319",
    "name": "패턴 인식",
    "description": "패턴 인식은 데이터 내의 패턴과 규칙성을 식별하는 계산적 과정으로, AI, 컴퓨터 과학, 심리학, 데이터 분석 등 다양한 분야에서 핵심적인 역할을 합니다. 이는 음성, 텍스트, 이미지 및 추상 데이터셋 내의 구조를 자동으로 인식하여 컴퓨터 비전, 음성 인식, OCR, 사기 탐지 등 지능형 시스템과 애플리케이션을 가능하게 합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/pattern-recognition/",
    "category": "자연어 & 멀티모달",
    "initial": "ㅍ"
  },
  {
    "id": "glossary-320",
    "name": "퍼지 매칭",
    "description": "퍼지 매칭은 데이터 내에서 쿼리에 대한 근사치 일치를 찾기 위한 검색 기법으로, 데이터의 변형, 오류, 불일치 등을 허용합니다. 데이터 정제, 레코드 연결, 텍스트 검색 등에 흔히 사용되며, Levenshtein 거리 및 Soundex와 같은 알고리즘을 활용하여 완전히 일치하지는 않지만 유사한 항목을 식별합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/fuzzy-matching/",
    "category": "자연어 & 멀티모달",
    "initial": "ㅍ"
  },
  {
    "id": "glossary-321",
    "name": "퍼플렉서티 AI",
    "description": "퍼플렉서티 AI는 고급 AI 기반 검색 엔진이자 대화형 도구로, 자연어 처리와 머신러닝을 활용하여 인용이 포함된 정확하고 맥락에 맞는 답변을 제공합니다. 연구, 학습, 전문적인 용도에 이상적이며, 여러 대형 언어 모델과 다양한 소스를 통합해 정확하고 실시간 정보 검색을 지원합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/perplexity-ai/",
    "category": "LLM & 생성형 AI",
    "initial": "ㅍ"
  },
  {
    "id": "glossary-322",
    "name": "편향",
    "description": "AI의 편향을 탐구하세요: 그 원인, 머신러닝에 미치는 영향, 실제 사례, 그리고 공정하고 신뢰할 수 있는 AI 시스템 구축을 위한 편향 완화 전략을 이해하세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/bias/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅍ"
  },
  {
    "id": "glossary-323",
    "name": "평균 절대 오차(MAE)",
    "description": "평균 절대 오차(MAE)는 회귀 모델 평가를 위한 머신러닝의 기본 지표입니다. 예측 오류의 평균 크기를 측정하여, 오류의 방향을 고려하지 않고 모델 정확도를 평가하는 간단하고 해석 가능한 방법을 제공합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/mean-absolute-error-mae/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅍ"
  },
  {
    "id": "glossary-324",
    "name": "평균 정밀도(mAP)",
    "description": "평균 정밀도(mAP)는 객체 탐지 모델을 평가하는 컴퓨터 비전의 핵심 지표로, 탐지 정확도와 위치 정확도를 하나의 스칼라 값으로 포착합니다. 자율주행, 감시, 정보 검색과 같은 작업에서 AI 모델의 벤치마킹 및 최적화에 널리 사용됩니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/mean-average-precision-map/",
    "category": "자연어 & 멀티모달",
    "initial": "ㅍ"
  },
  {
    "id": "glossary-325",
    "name": "포즈 추정",
    "description": "포즈 추정은 이미지나 비디오에서 사람이나 객체의 위치와 방향을 주요 지점을 식별하고 추적하여 예측하는 컴퓨터 비전 기술입니다. 이는 스포츠 분석, 로보틱스, 게임, 자율주행 등 다양한 응용 분야에서 필수적입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/pose-estimation/",
    "category": "자연어 & 멀티모달",
    "initial": "ㅍ"
  },
  {
    "id": "glossary-326",
    "name": "품사 태깅(Part-of-Speech Tagging)",
    "description": "품사 태깅(POS 태깅)은 계산 언어학과 자연어 처리(NLP)에서 핵심적인 작업입니다. 이는 텍스트 내 각 단어에 대해 해당 정의와 문장 내 맥락에 따라 적합한 품사를 할당하는 과정을 의미합니다. 주요 목적은 단어를 명사, 동사, 형용사, 부사 등과 같은 문법적 범주로 분류하여, 기계가 인간 언어를 보다 효과적으로 처리하고 이해할 수 있도록 돕는 것입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/part-of-speech-tagging/",
    "category": "자연어 & 멀티모달",
    "initial": "ㅍ"
  },
  {
    "id": "glossary-327",
    "name": "퓨샷 러닝(Few-Shot Learning)",
    "description": "퓨샷 러닝은 소수의 라벨링된 예시만으로도 모델이 정확한 예측을 할 수 있도록 하는 머신러닝 접근법입니다. 기존 감독학습 방식과 달리, 제한된 데이터로부터 일반화하는 데 집중하며, 메타러닝, 전이 학습, 데이터 증강과 같은 기법을 활용합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/few-shot-learning/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅍ"
  },
  {
    "id": "glossary-328",
    "name": "프레셰 인셉션 거리(FID)",
    "description": "프레셰 인셉션 거리(FID)는 생성 모델, 특히 GAN이 생성한 이미지의 품질을 평가하는 데 사용되는 지표입니다. FID는 생성된 이미지와 실제 이미지의 분포를 비교하여 이미지의 품질과 다양성을 보다 총체적으로 측정합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/frechet-inception-distance-fid/",
    "category": "자연어 & 멀티모달",
    "initial": "ㅍ"
  },
  {
    "id": "glossary-329",
    "name": "프레이즈(Frase)",
    "description": "프레이즈(Frase)에 대한 기본 정보를 알아보세요. AI 기반의 SEO 최적화 콘텐츠 제작 도구의 주요 기능, 장단점, 대안들을 확인할 수 있습니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/frase/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅍ"
  },
  {
    "id": "glossary-330",
    "name": "프롬프트",
    "description": "LLM 분야에서 프롬프트란 모델의 출력을 안내하는 입력 텍스트를 의미합니다. 효과적인 프롬프트 작성법, 제로샷·원샷·퓨샷·체인오브쏘트 기법을 통해 AI 언어 모델의 응답 품질을 높이는 방법을 알아보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/prompt/",
    "category": "LLM & 생성형 AI",
    "initial": "ㅍ"
  },
  {
    "id": "glossary-331",
    "name": "하이퍼파라미터 튜닝",
    "description": "하이퍼파라미터 튜닝은 학습률, 정규화와 같은 파라미터를 조정하여 모델 성능을 최적화하는 머신러닝의 기본 과정입니다. 그리드 서치, 랜덤 서치, 베이지안 최적화 등 다양한 방법을 알아보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/hyperparameter-tuning/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅎ"
  },
  {
    "id": "glossary-332",
    "name": "학년 수준",
    "description": "가독성에서 학년 수준이 무엇을 의미하는지, Flesch-Kincaid와 같은 공식으로 어떻게 계산되는지, 그리고 왜 콘텐츠를 독자의 읽기 능력에 맞추는 데 중요한지 알아보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/grade-level/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅎ"
  },
  {
    "id": "glossary-333",
    "name": "학습 곡선",
    "description": "인공지능에서의 학습 곡선은 모델의 학습 성능과 데이터셋 크기 또는 학습 반복과 같은 변수 간의 관계를 그래프로 나타내며, 편향-분산 트레이드오프 진단, 모델 선택, 학습 과정 최적화에 도움을 줍니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/learning-curve/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅎ"
  },
  {
    "id": "glossary-334",
    "name": "학습 데이터",
    "description": "학습 데이터는 AI 알고리즘을 교육하는 데 사용되는 데이터셋으로, 패턴을 인식하고, 의사 결정을 내리며, 결과를 예측할 수 있도록 합니다. 이 데이터는 텍스트, 숫자, 이미지, 동영상 등을 포함할 수 있으며, 효과적인 AI 모델 성능을 위해 고품질, 다양성, 그리고 정확한 라벨링이 필수적입니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/training-data/",
    "category": "자연어 & 멀티모달",
    "initial": "ㅎ"
  },
  {
    "id": "glossary-335",
    "name": "학습 오류",
    "description": "AI와 머신러닝에서 학습 오류는 모델이 학습 중 예측한 출력과 실제 출력 간의 차이를 의미합니다. 이는 모델 성능을 평가하는 주요 지표이지만, 과적합 또는 과소적합을 피하기 위해 테스트 오류와 함께 고려해야 합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/training-error/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅎ"
  },
  {
    "id": "glossary-336",
    "name": "합성 데이터",
    "description": "합성 데이터는 실제 데이터를 모방하여 인위적으로 생성된 정보입니다. 알고리즘과 컴퓨터 시뮬레이션을 사용하여 실제 데이터를 대체하거나 보완하기 위해 만들어집니다. AI에서 합성 데이터는 기계 학습 모델의 학습, 테스트, 검증에 매우 중요합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/synthetic-data/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅎ"
  },
  {
    "id": "glossary-337",
    "name": "합성곱 신경망(CNN)",
    "description": "합성곱 신경망(CNN)은 이미지와 같은 구조화된 그리드 데이터를 처리하도록 설계된 인공 신경망의 한 유형입니다. CNN은 이미지 분류, 객체 탐지, 이미지 분할 등 시각 데이터와 관련된 작업에서 특히 효과적입니다. 인간 두뇌의 시각 처리 메커니즘을 모방하여 컴퓨터 비전 분야의 핵심 기술로 자리잡고 있습니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/convolutional-neural-network-cnn/",
    "category": "자연어 & 멀티모달",
    "initial": "ㅎ"
  },
  {
    "id": "glossary-338",
    "name": "해자(Moats)",
    "description": "AI에서 '해자(Moat)'는 규모의 경제, 네트워크 효과, 독점 기술, 높은 전환 비용, 데이터 해자 등과 같은 지속 가능한 경쟁 우위를 의미하며, 기업이 시장 리더십을 유지하고 경쟁을 막는 데 도움이 됩니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/moats/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅎ"
  },
  {
    "id": "glossary-339",
    "name": "허깅페이스 트랜스포머",
    "description": "허깅페이스 트랜스포머는 NLP, 컴퓨터 비전, 오디오 처리 등 머신러닝 작업을 위한 트랜스포머 모델 구현을 손쉽게 할 수 있는 선도적인 오픈소스 파이썬 라이브러리입니다. 수천 개의 사전 학습된 모델에 접근할 수 있으며, PyTorch, TensorFlow, JAX와 같은 인기 프레임워크를 지원합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/hugging-face-transformers/",
    "category": "자연어 & 멀티모달",
    "initial": "ㅎ"
  },
  {
    "id": "glossary-340",
    "name": "헌법적 인공지능(Constitutional AI)",
    "description": "헌법적 인공지능(Constitutional AI)은 인공지능 시스템을 헌법 원칙과 법적 프레임워크에 맞게 정렬하여, AI 운영이 헌법이나 기본 법률 문서에 명시된 권리, 특권, 가치들을 준수하도록 하여 윤리적·법적 준수를 보장하는 것을 의미합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/constitutional-ai/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅎ"
  },
  {
    "id": "glossary-341",
    "name": "협동로봇(코봇, Cobots)",
    "description": "협동로봇(코봇)의 기원, 안전 기능, AI 통합, 다양한 산업 분야에서의 활용, 장점과 한계에 대해 알아보세요. 코봇이 안전한 인간-로봇 상호작용을 가능하게 하고 혁신을 촉진하는 방법을 배울 수 있습니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/collaborative-robots-cobots/",
    "category": "보안 & 프라이버시",
    "initial": "ㅎ"
  },
  {
    "id": "glossary-342",
    "name": "혼동 행렬",
    "description": "혼동 행렬은 분류 모델의 성능을 평가하는 머신러닝 도구로, 참/거짓 양성 및 음성의 세부 정보를 제공하여 정확도를 넘어선 인사이트를 제공하며, 특히 불균형 데이터셋에서 유용합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/confusion-matrix/",
    "category": "자연어 & 멀티모달",
    "initial": "ㅎ"
  },
  {
    "id": "glossary-343",
    "name": "확장성(Extensibility)",
    "description": "AI 확장성이란 AI 시스템이 전이 학습, 다중 작업 학습, 모듈형 설계 등과 같은 기법을 통해 유연성과 매끄러운 통합을 실현하며, 대대적인 재학습 없이 새로운 도메인, 작업, 데이터셋으로 능력을 확장하는 것을 의미합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/extensibility/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅎ"
  },
  {
    "id": "glossary-344",
    "name": "환각(Hallucination)",
    "description": "언어 모델에서의 환각은 AI가 그럴듯하게 보이지만 실제로는 부정확하거나 조작된 텍스트를 생성하는 현상입니다. 원인, 탐지 방법, 그리고 AI 결과물에서 환각을 줄이기 위한 전략에 대해 알아보세요.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/hallucination/",
    "category": "LLM & 생성형 AI",
    "initial": "ㅎ"
  },
  {
    "id": "glossary-345",
    "name": "활성화 함수",
    "description": "활성화 함수는 인공 신경망에서 필수적인 요소로, 비선형성을 도입하여 복잡한 패턴 학습을 가능하게 합니다. 이 글에서는 활성화 함수의 목적, 유형, 도전 과제, 그리고 AI, 딥러닝, 신경망에서의 핵심 응용 분야를 살펴봅니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/activation-functions/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅎ"
  },
  {
    "id": "glossary-346",
    "name": "휴리스틱",
    "description": "휴리스틱은 AI에서 경험적 지식과 직관적 규칙을 활용하여 복잡한 탐색 문제를 단순화하고, A*, 힐 클라이밍 등과 같은 알고리즘이 유망한 경로에 집중할 수 있도록 하여 효율성을 높여주는 빠르고 만족스러운 해결책을 제공합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/heuristics/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅎ"
  },
  {
    "id": "glossary-347",
    "name": "휴먼 인 더 루프",
    "description": "휴먼 인 더 루프(HITL)는 AI 및 머신러닝 접근 방식으로, AI 시스템의 학습, 조정 및 적용 과정에 인간의 전문성을 통합하여 정확성을 높이고 오류를 줄이며 윤리적 준수를 보장합니다.",
    "url": "https://www.flowhunt.io/ko/%EC%9A%A9%EC%96%B4%EC%A7%91/human-in-the-loop/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅎ"
  },
  {
    "id": "glossary-348",
    "name": "AI 방화벽",
    "description": "AI 방화벽은 인공지능 시스템, 특히 대형 언어 모델(LLM)과 생성형 AI API를 위해 설계된 보안 계층으로, 기존 방화벽을 우회하는 고유한 공격과 오용을 자연어 입력 및 출력의 상황 인식 검사를 통해 방어합니다.",
    "url": "https://www.flowhunt.io/ko/glossary/ai-firewall/",
    "category": "보안 & 프라이버시",
    "initial": "A"
  },
  {
    "id": "glossary-349",
    "name": "제로 클릭 검색",
    "description": "제로 클릭 검색이란 검색 엔진이 사용자의 쿼리에 대해 SERP에서 직접 답변을 제공하여, 어떤 웹사이트도 클릭할 필요가 없게 만드는 현상을 말합니다. 이러한 검색은 특화 스니펫, 지식 패널, AI 생성 요약 등과 같은 기능을 통해 만족됩니다.",
    "url": "https://www.flowhunt.io/ko/glossary/zero-click-search/",
    "category": "머신러닝 & 딥러닝",
    "initial": "ㅈ"
  }
];
