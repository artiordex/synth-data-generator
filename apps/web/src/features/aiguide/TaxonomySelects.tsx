/**
 * 파일명: TaxonomySelects.tsx
 * 경로: apps/web/src/features/aiguide/TaxonomySelects.tsx
 * 목적: 공공데이터포털(DATA_GO_KR) 2026-09 표준 분류체계 2단(대분류-소분류) 셀렉트 박스 컴포넌트
 * 작성자: 개발팀
 * 작성일: 2026-09-17
 */
import React, { useMemo } from 'react';

export interface DataGoKrTaxonomy {
  source: string;
  taxonomyVersion: string;
  categories: Record<string, string[]>;
}

export const DATA_GO_KR_TAXONOMY: DataGoKrTaxonomy = {
  source: 'DATA_GO_KR',
  taxonomyVersion: '2026-09',
  categories: {
    일반공공행정: [
      '국정운영',
      '일반행정',
      '재정·금융',
      '법제',
      '정부자원관리',
      '지방행정·재정지원',
    ],
    공공질서및안전: [
      '경찰',
      '법무및검찰',
      '안전관리',
      '해양경비',
    ],
    과학기술: [
      '과학기술연구',
      '과학기술진흥',
    ],
    교육: [
      '고등교육',
      '교육일반',
      '유아및초·중등교육',
      '평생·직업교육',
    ],
    국방: [
      '병무행정',
      '방위력개선',
      '병력운영',
      '국방일반행정',
      '전력유지',
    ],
    농림: [
      '농업·농촌',
      '임업·산촌',
    ],
    해양수산: [
      '해양수산·어촌',
    ],
    문화체육관광: [
      '관광',
      '문화예술',
      '문화재',
      '문화체육관광일반',
      '체육',
    ],
    보건: [
      '건강보험',
      '보건의료',
      '식품의약품안전',
    ],
    사회복지: [
      '공적연금',
      '기초생활보장',
      '고용노동',
      '노인·청소년',
      '사회복지일반',
      '보육·가족및여성',
      '보훈',
      '주택',
      '취약계층지원',
    ],
    '산업·통상·중소기업': [
      '통상',
      '무역및투자유치',
      '산업·중소기업일반',
      '산업금융지원',
      '산업기술지원',
      '산업진흥·고도화',
      '에너지및자원개발',
    ],
    지역개발: [
      '산업단지',
      '수자원',
      '지역및도시',
    ],
    교통및물류: [
      '도로',
      '도시철도',
      '물류등기타',
      '철도',
      '항공·공항',
      '해운·항만',
    ],
    통신: [
      '방송통신',
      '우정',
    ],
    '통일·외교': [
      '외교',
      '통일',
    ],
    환경: [
      '대기',
      '상하수도·수질',
      '자연',
      '폐기물',
      '해양환경',
      '환경일반',
    ],
  },
};

export const MAJOR_CATEGORIES = Object.keys(DATA_GO_KR_TAXONOMY.categories);

/**
 * 대분류와 소분류를 표준 표시 문자열로 결합함 (예: "보건 - 식품의약품안전" 또는 "보건")
 */
export function formatThemeLabel(major: string, sub: string): string {
  if (!major) return '';
  if (!sub) return major;
  return `${major} - ${sub}`;
}

/**
 * 문자열을 파싱하여 대분류와 소분류를 추출함.
 * 기존 약칭이나 레거시 값(예: "보건의료 - 의약품", "교통물류", "식품안전")도 지능적으로 매핑함.
 */
export function parseThemeLabel(raw: string): { major: string; sub: string } {
  if (!raw || !raw.trim()) {
    return { major: '', sub: '' };
  }

  const trimmed = raw.trim();

  // 1. 구분자(" - ", "-", "/", ">")로 분할된 경우
  const separatorMatch = trimmed.match(/^(.+?)\s*(?:[-–—/>]|->)\s*(.+)$/);
  if (separatorMatch) {
    const part1 = separatorMatch[1].trim();
    const part2 = separatorMatch[2].trim();

    // part1이 정확한 대분류인 경우
    if (DATA_GO_KR_TAXONOMY.categories[part1]) {
      const subs = DATA_GO_KR_TAXONOMY.categories[part1];
      const matchedSub = subs.find(s => s === part2 || s.includes(part2) || part2.includes(s));
      return { major: part1, sub: matchedSub || part2 };
    }

    // part1이 레거시/유사 명칭인 경우
    const guessedMajor = findMajorByAlias(part1);
    if (guessedMajor) {
      const subs = DATA_GO_KR_TAXONOMY.categories[guessedMajor];
      const matchedSub = subs.find(s => s === part2 || s.includes(part2) || part2.includes(s));
      return { major: guessedMajor, sub: matchedSub || subs[0] || '' };
    }
  }

  // 2. 입력값이 정확한 대분류인 경우
  if (DATA_GO_KR_TAXONOMY.categories[trimmed]) {
    return { major: trimmed, sub: '' };
  }

  // 3. 입력값이 특정 소분류와 일치하는 경우
  for (const [major, subs] of Object.entries(DATA_GO_KR_TAXONOMY.categories)) {
    for (const sub of subs) {
      if (trimmed === sub || trimmed.includes(sub) || sub.includes(trimmed)) {
        return { major, sub };
      }
    }
  }

  // 4. 별칭 및 부분 일치 처리
  const guessedMajor = findMajorByAlias(trimmed);
  if (guessedMajor) {
    return { major: guessedMajor, sub: '' };
  }

  return { major: '', sub: '' };
}

function findMajorByAlias(text: string): string | null {
  const norm = text.replace(/\s+/g, '').replace(/[·]/g, '');

  for (const major of MAJOR_CATEGORIES) {
    const normMajor = major.replace(/\s+/g, '').replace(/[·]/g, '');
    if (norm.includes(normMajor) || normMajor.includes(norm)) {
      return major;
    }
  }

  if (/식품|의약|병원|의료|약품|보건/.test(norm)) return '보건';
  if (/교통|지하철|철도|버스|도로|물류|항만|공항/.test(norm)) return '교통및물류';
  if (/재정|금융|예산|세무|국고|행정/.test(norm)) return '일반공공행정';
  if (/토지|도시|단지|수자원|지역/.test(norm)) return '지역개발';
  if (/복지|연금|노인|청소년|보육|가족|보훈|주택/.test(norm)) return '사회복지';
  if (/환경|대기|미세먼지|수질|폐기물/.test(norm)) return '환경';
  if (/과학|기술|연구|진흥/.test(norm)) return '과학기술';
  if (/교육|학교|대학/.test(norm)) return '교육';
  if (/국방|군사|병무/.test(norm)) return '국방';
  if (/농업|농촌|임업|산림|농림/.test(norm)) return '농림';
  if (/해양|수산|어촌/.test(norm)) return '해양수산';
  if (/문화|예술|관광|체육|문화재/.test(norm)) return '문화체육관광';
  if (/산업|통상|무역|에너지|중소기업/.test(norm)) return '산업·통상·중소기업';
  if (/통신|방송|우정/.test(norm)) return '통신';
  if (/외교|통일/.test(norm)) return '통일·외교';
  if (/경찰|검찰|치안|소방|안전/.test(norm)) return '공공질서및안전';

  return null;
}

interface TaxonomySelectsProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  className?: string;
  selectClassName?: string;
}

/**
 * 공공데이터포털 분류체계 2단(대분류-소분류) 드롭다운 컴포넌트
 */
export function TaxonomySelects({
  value,
  onChange,
  disabled = false,
  className = '',
  selectClassName = '',
}: TaxonomySelectsProps) {
  const { major, sub } = useMemo(() => parseThemeLabel(value), [value]);

  const subCategories = useMemo(() => {
    return major ? DATA_GO_KR_TAXONOMY.categories[major] || [] : [];
  }, [major]);

  const handleMajorChange = (newMajor: string) => {
    if (!newMajor) {
      onChange('');
      return;
    }
    const availableSubs = DATA_GO_KR_TAXONOMY.categories[newMajor] || [];
    // 기존에 선택된 소분류가 새로 선택한 대분류의 하위 항목에 포함되어 있으면 유지, 없으면 빈 값
    const nextSub = availableSubs.includes(sub) ? sub : '';
    onChange(formatThemeLabel(newMajor, nextSub));
  };

  const handleSubChange = (newSub: string) => {
    if (!major) return;
    onChange(formatThemeLabel(major, newSub));
  };

  const baseSelectStyle =
    selectClassName ||
    'w-full bg-surface-muted/20 hover:bg-surface-muted/40 focus:bg-surface border border-subtle/60 focus:border-accent rounded px-2.5 py-1.5 text-xs text-fg font-medium outline-none transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed';

  return (
    <div className={`grid grid-cols-2 gap-2 ${className}`}>
      {/* 1단: 대분류 셀렉트 박스 */}
      <select
        value={major}
        disabled={disabled}
        onChange={e => handleMajorChange(e.target.value)}
        className={baseSelectStyle}
        aria-label="분류체계 대분류"
      >
        <option value="" className="bg-surface text-fg">
          대분류 선택
        </option>
        {MAJOR_CATEGORIES.map(cat => (
          <option key={cat} value={cat} className="bg-surface text-fg">
            {cat}
          </option>
        ))}
      </select>

      {/* 2단: 소분류 셀렉트 박스 */}
      <select
        value={sub}
        disabled={disabled || !major}
        onChange={e => handleSubChange(e.target.value)}
        className={baseSelectStyle}
        aria-label="분류체계 소분류"
      >
        <option value="" className="bg-surface text-fg">
          {major ? '소분류 선택' : '대분류 먼저 선택'}
        </option>
        {subCategories.map(subCat => (
          <option key={subCat} value={subCat} className="bg-surface text-fg">
            {subCat}
          </option>
        ))}
      </select>
    </div>
  );
}
