# IREN Macro Monitor V1

모바일용 정적 웹 대시보드입니다. 화면은 `data.json`을 즉시 읽고, GitHub Actions가 30분마다 최신 시장 데이터로 갱신합니다.

## 배포
1. 새 public repository 생성: `iren-macro-monitor` 추천
2. ZIP의 모든 파일/폴더 업로드
3. GitHub → Settings → Pages
4. Build and deployment → Deploy from a branch
5. Branch `main`, folder `/ (root)` → Save
6. 잠시 후 `https://<사용자명>.github.io/iren-macro-monitor/` 주소 생성

## 자동 갱신
`.github/workflows/update-data.yml`이 30분마다 `scripts/update_data.py`를 실행해 `data.json`을 갱신합니다. GitHub 스케줄 실행은 지연될 수 있습니다.

## Macro Lab 연결
`data.json`의 `macro_lab_url`에 기존 Streamlit 주소를 넣으면 하단 `Open Macro Lab →` 버튼이 활성화됩니다.

CTA 관련 표시는 proprietary CTA 포지션이 아니라 가격 모멘텀 프록시입니다.
