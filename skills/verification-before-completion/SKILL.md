---
name: verification-before-completion
description: 작업 완료, 수정됨, 실행 성공을 주장하기 전에 사용. execute_code 실제 출력을 확인한 후에만 완료 선언 가능.
---

# 완료 전 검증 (Verification Before Completion)

## Iron Law

```
검증 증거 없이는 완료 선언 불가
이번 메시지에서 execute_code를 실행하지 않았다면, 성공했다고 주장할 수 없다.
```

## 검증 게이트

완료/성공/통과를 주장하기 전 반드시:

1. **특정**: 이 주장을 증명하는 `execute_code`가 무엇인가?
2. **실행**: 전체 코드 실행 (부분 실행 금지)
3. **확인**: stdout 전체 읽기, 에러 여부 확인
4. **검증**: 출력이 주장을 실제로 뒷받침하는가?
   - NO → 실제 상태를 증거와 함께 보고
   - YES → 증거(stdout 인용)와 함께 주장

## 주장별 필수 증거

| 주장 | 필요한 증거 | 불충분한 것 |
|------|-----------|------------|
| 데이터 로드 성공 | `df.shape` stdout 출력 | "로드됐을 것" |
| 모델 학습 완료 | CV 점수 stdout 출력 | 코드 작성 |
| 가설 검증 | 수치 + p-value stdout 출력 | 방향만 언급 |
| 분석 완료 | `verify-report` execute_code 재실행 결과 | 이전 실행 결과 |

## Red Flags

| 생각 | 현실 |
|------|------|
| "should", "probably", "아마" 사용 | 검증 안 한 것 |
| execute_code 전 "완료!", "됐어요!" | Iron Law #3 위반 |
| 이전 iteration 결과로 완료 주장 | 재실행 필요 |
