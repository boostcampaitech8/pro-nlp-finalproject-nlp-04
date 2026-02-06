# Sample Plan 16

> A Technical plan regarding 정확한 정적 분석 및 PR 통합

*생성 방법: blueprint*

---

## 목차

- [1. 1. 분석 룰셋 커스터마이징](#1-1.-분석-룰셋-커스터마이징)
- [2. 2. CI/CD 파이프라인 연동](#2-2.-ci/cd-파이프라인-연동)
- [3. 3. 리포트 포맷](#3-3.-리포트-포맷)

---

## 2. 2. CI/CD 파이프라인 연동

GitHub Actions 워크플로우를 활용해 **코드 푸시 시 자동 분석 실행 → PR 코멘트 작성** 프로세스를 다음과 같이 설계합니다.  

#### 🔄 트리거 조건  
- **이벤트**: `push` (개발 브랜치), `pull_request` (PR 생성/업데이트)  
- **필터링**: 분석 대상 파일 변경 시에만 실행 (예: `**.py`, `**.js` 등)  

#### 🛠️ 워크플로우 구성  
```yaml
jobs:
  static-analysis:
    runs-on: ubuntu-latest
    steps:
      - name: 코드 체크아웃  
        uses: actions/checkout@v3

      - name: 분석 봇 실행  
        run: |
          # 분석 도구/커스텀 스크립트 실행 (예: `python analyze.py`)
          ./run_analysis.sh
        # 환경 변수 또는 아티팩트로 결과 저장 (JSON/텍스트 형식)

      - name: PR 코멘트 작성  
        uses: peter-evans/create-or-update-comment@v3  
        with:  
          token: ${{ secrets.GITHUB_TOKEN }}  
          issue-number: ${{ github.event.pull_request.number }}  
          body-file: ${{ env.ANALYSIS_RESULT_PATH }}  # 분석 결과 파일 경로  
          edit-mode: replace  # 기존 코멘트 업데이트
```

#### 📝 코멘트 포맷  
- **헤더**: 분석 도구명/버전, 실행 시간  
- **바디**:  
  - 🔴 **주요 이슈**: 우선순위별 분류 (Critical/High/Medium)  
  - 📊 **통계**: 총 이슈 수, 신규/기존 이슈 비교  
  - 🛠️ **권장 조치**: 각 이슈별 해결 가이드 링크  

#### 🔐 보안 및 최적화  
- **권한 관리**: `GITHUB_TOKEN`에 `pull_request: write` 권한만 부여  
- **중복 방지**: `edit-mode: replace`로 동일 코멘트 업데이트  
- **병렬성 제어**: 동일 PR에 대한 중복 실행 방지 (예: `concurrency` 그룹 설정)  

#### 📈 확장성  
- 분석 결과를 **아티팩트**로 저장해 히스토리 추적 가능  
- Slack/MS Teams 등 외부 툴과 연동해 알림 전파 지원  

이 설계를 통해 코드 변경 시 실시간 피드백 루프를 구축하고, 리뷰어의 수동 검토 부담을 줄일 수 있습니다.
