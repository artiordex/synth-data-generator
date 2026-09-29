/**
 * 파일명: AsyncFeatureBoundary.tsx
 * 경로: apps/web/src/components/AsyncFeatureBoundary.tsx
 * 목적: 비동기 화면 로딩 오류를 사용자에게 안내함
 * 작성자: 개발팀
 * 작성일: 2026-09-29
 * 수정일: 2026-09-29
 */
import React from 'react';

interface AsyncFeatureBoundaryProps {
  featureName: string;
  children: React.ReactNode;
}

interface AsyncFeatureBoundaryState {
  hasError: boolean;
}

/** 비동기 화면 하위 트리의 렌더링 오류를 격리함 */
export class AsyncFeatureBoundary extends React.Component<
  AsyncFeatureBoundaryProps,
  AsyncFeatureBoundaryState
> {
  state: AsyncFeatureBoundaryState = { hasError: false };

  /** 오류 경계 상태를 실패 화면으로 전환함 */
  static getDerivedStateFromError(): AsyncFeatureBoundaryState {
    return { hasError: true };
  }

  /** 하위 화면 로딩 오류를 기록함 */
  componentDidCatch(error: Error) {
    console.error(`Failed to load ${this.props.featureName} feature.`, error);
  }

  /** 오류 상태 또는 정상 하위 화면을 렌더링함 */
  render() {
    if (this.state.hasError) {
      return (
        <section className="ui-panel p-6" role="alert">
          <h2 className="ui-section-title">{this.props.featureName} 화면을 불러오지 못했습니다.</h2>
          <p className="ui-help-text mt-2">화면 파일을 불러오는 중 오류가 발생했습니다.</p>
          <button
            type="button"
            className="ui-button-secondary mt-4"
            onClick={() => window.location.reload()}
          >
            새로고침 후 다시 시도
          </button>
        </section>
      );
    }

    return this.props.children;
  }
}
