# JSON Schema (경계별 전달용)

각 파일은 JSON Schema 2020-12이며 필요한 `$defs`를 모두 포함해 **혼자 사용할 수 있다**(`jsonschema` 등 구현에서 파일 하나만 로드). 원본은 스키마 프로젝트 `work/contracts/`, 이 파일들은 거기서 생성된 `generated/schemas/standalone/`의 복사본이다.

| 컴포넌트 | 방향 | 파일 | 내용 |
|---|---|---|---|
| 프론트 | 입력 | [`FrontendInput.json`](FrontendInput.json) | 응답 문장과 턴 실패 신호. |
| 프론트 | 출력 | [`FrontendMessage.json`](FrontendMessage.json) | 프론트가 LangGraph로 보내는 것 하나. |
| 사람 개입 | 입력 | [`StaffConsoleInput.json`](StaffConsoleInput.json) | 직원 알림(세션 식별 포함), 턴 실패 신호, 개입 결정 결과. |
| 사람 개입 | 출력 | [`InterventionDecision.json`](InterventionDecision.json) | 직원·의료진의 재개·종료. |
| LangGraph | 입력 | [`OrchestratorInput.json`](OrchestratorInput.json) | 턴 시작 입력과 세션 상태. |
| LangGraph | 출력 | [`OrchestratorOutput.json`](OrchestratorOutput.json) | 턴 종류, 세션 정보 생성, 대화 로그 항목, 턴 실패 신호, 개입 결정 결과, 결과 전달 호출 여부. |
| LoRA-A | 입력 | [`UtteranceParserInput.json`](UtteranceParserInput.json) | 업무분담 LoRA-A Input(session_id·question_id·question_schema·user_utterance·relevant_state)에 대응. 현재 1턴을 기본으로 하고 필요한 상태만 더한다는 업무분담 원칙을 따른다. |
| LoRA-A | 출력 | [`ParserOutput.json`](ParserOutput.json) | 항목 목록. 빈 발화면 빈 목록. |
| 정규화·검증 | 입력 | [`AnswerNormalizerInput.json`](AnswerNormalizerInput.json) | 항목 목록과 관련 문항의 규칙·현재값·확인 대기·기다리는 답. |
| 정규화·검증 | 출력 | [`NormalizerOutput.json`](NormalizerOutput.json) | 항목별 검사와 빠진 필수 슬롯. |
| 상태 판정 | 입력 | [`AnswerJudgeInput.json`](AnswerJudgeInput.json) | 항목·검사·발화 원문·위험 표현·직전 응답 지시·확인 대기 목록·후속 문항·슬롯 목록. |
| 상태 판정 | 출력 | [`JudgeOutput.json`](JudgeOutput.json) | 판정, 무효화 대상 문항, 발화 판정. |
| 저장 판단 | 입력 | [`RecordWriterInput.json`](RecordWriterInput.json) | 판정·무효화 대상 문항·슬롯 목록·기록 대상 슬롯의 응답 기록. |
| 저장 판단 | 출력 | [`StoreResult.json`](StoreResult.json) | 저장 결정과 저장 결과 요약. |
| Plan 결정 | 입력 | [`DialoguePlannerInput.json`](DialoguePlannerInput.json) | 턴 종류, 이번 턴 판정들, 저장 뒤 응답 기록, 진행 기록의 사실, Plan 기록, 문항 정의 전체. |
| Plan 결정 | 출력 | [`PlannerOutput.json`](PlannerOutput.json) | 응답 지시, 흐름, 직원 알림, 진행 기록 갱신, Plan 기록 갱신. |
| LoRA-B | 입력 | [`ResponseGeneratorInput.json`](ResponseGeneratorInput.json) | 응답 지시와 발화. |
| LoRA-B | 출력 | [`GeneratorOutput.json`](GeneratorOutput.json) | 응답 문장. |
| 결과 전달 | 입력 | [`DispatchInput.json`](DispatchInput.json) | 세션 정보·응답 기록·건너뜀·확인 중단·세션 상태·중지 이력·문항 정의(턴 쓰기 반영 뒤). |
| 결과 전달 | 출력 | [`DispatchOutput.json`](DispatchOutput.json) | 전달 기록 한 건. 밖으로 넘기는 문진 결과의 형식은 받는 곳이 정해지면 정한다(이 스키마 밖). |
| 문항 정의 저장소 | 저장소 상태 | [`QuestionBank.json`](QuestionBank.json) | 한 버전의 문항 정의 전체. 운영 중 바뀌지 않는다. |
| 기록 저장소 | 저장소 상태 | [`SessionStore.json`](SessionStore.json) | 세션 하나의 기록 전체. |

사용 예(Python):

```python
import json
from jsonschema import Draft202012Validator
schema = json.load(open("schemas/ParserOutput.json", encoding="utf-8"))
Draft202012Validator(schema).validate({"items": []})
```

Schema는 값의 구조만 검사한다. 발화를 올바른 의도로 분류했는지, 문장이 적절한지는 각 컴포넌트가 검증한다.
