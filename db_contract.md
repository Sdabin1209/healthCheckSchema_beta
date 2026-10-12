# DB Contract (db_contract.md)

> 담당: 송다빈 · 대상: 문항 정의 저장소(`QuestionBank`)와 기록 저장소(`SessionStore`). 작업문서의 “DB 저장: 현재값·수정 이력·진행 상태”에 해당한다.  
> 효과 규칙은 스키마 프로젝트 `rules/session_store.md`(9-2절)·`record_writer.md`(7절)·`preconditions.md`(0-1절)에서 옮겼고, 본문의 참조 구현(`tests/e2e/run_e2e.py`의 `apply_*`)으로 케이스 예시 222/223턴의 최종 상태를 재현해 확인했다.

## 1. 저장소 두 개

| 저장소 | 계약 | 쓰는 쪽 | 읽는 쪽 | 성격 |
|---|---|---|---|---|
| 문항 정의 저장소 (Question Bank) | `QuestionBank` | 문진 설계자(시스템 밖, 운영 중 변경 없음) | LangGraph, LoRA-A, 정규화·검증, 상태 판정, 저장 판단, Plan | 버전별 읽기 전용. 세션은 만들어질 때의 버전을 끝까지 쓴다(J1). |
| 기록 저장소 (Session Store) | `SessionStore` | 필드마다 하나: 아래 §2 | LangGraph, LoRA-A, 정규화·검증, 상태 판정, 저장 판단, Plan, 결과 전달, 직원 화면(세션 식별) | 세션 하나의 기록 전체. 저장소는 판단하지 않고 받은 쓰기를 정해진 효과대로만 반영한다. |

작업문서 용어와의 대응: **현재값** = `answer_records[].current_value`, **수정 이력(Revision)** = `answer_records[].history`(오래된 것부터), **진행 상태** = `progress_record`(+ `planner_record`의 횟수), **Finalization 기록** = 결과 전달 + `dispatch_log`.

## 2. 기록 저장소(SessionStore) 구조

| 섹션 | 타입 | 뜻 | 쓰는 쪽 (하나) | 쓰기 값 | 읽는 쪽 (시점) |
|---|---|---|---|---|---|
| `session_info` | SessionInfo | **세션 정보** — LangGraph가 세션을 만들 때 한 번 쓴다. | LangGraph — 세션을 만들 때 한 번 | `OrchestratorOutput.session_info_created` | 사람 개입(세션 식별만); LangGraph(턴 맨 앞, 턴 시작); 결과 전달(턴 쓰기 반영 뒤) |
| `answer_records` | array<SlotRecord> | **응답 기록** — 슬롯별 기록. 저장 판단만 쓴다. | 저장 판단만 | `StoreResult.store_decisions` | LoRA-A(턴 시작); 정규화·검증(턴 시작); 상태 판정(턴 시작); 저장 판단(턴 시작); Plan 결정(저장 결정 반영 뒤); 결과 전달(턴 쓰기 반영 뒤) |
| `progress_record` | ProgressRecord | **진행 기록** — Plan만 쓴다. | Plan만 | `PlannerOutput.progress_record_update` | LangGraph(턴 시작); LoRA-A(턴 시작); 정규화·검증(턴 시작); 상태 판정(턴 시작); Plan 결정(턴 시작); 결과 전달(턴 쓰기 반영 뒤) |
| `planner_record` | PlannerRecord | **Plan 기록** — Plan만 쓰고 읽는다. | Plan만 | `PlannerOutput.planner_record_update` | Plan 결정(턴 시작) |
| `dialogue_log` | array<LogEntry> | **대화 로그** — LangGraph만 쓴다. 시스템 안에서 읽는 컴포넌트는 없다. | LangGraph만 (턴 끝, 실패한 턴도) | `OrchestratorOutput.log_entry` | — (시스템 안에서 읽는 컴포넌트 없음) |
| `dispatch_log` | array<DispatchRecord> | **전달 기록** — 결과 전달만 쓴다. | 결과 전달만 (쓰기 확정 뒤) | `DispatchOutput.dispatch_record` | — (시스템 안에서 읽는 컴포넌트 없음) |

JSON Schema: [`schemas/SessionStore.json`](schemas/SessionStore.json), [`schemas/QuestionBank.json`](schemas/QuestionBank.json)

### 2.1 응답 기록 — 슬롯 하나(`SlotRecord`)

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `slot` | 필수 | SlotRef | **슬롯** — 이 답 기록이 속한 문항·반복 행·슬롯의 식별자. |
| `current_value` | 필수 | CurrentValue | **현재값** — 지금 기록. |
| `risk_mark` | 필수 | RiskResponse \| null | **위험 표시** — 현재값의 위험 기준. |
| `history` | 필수 | array<Value> | **이력** — 이전 답 값들(오래된 것부터). |
| `pending` | 필수 | PendingRecord \| null | **확인 대기** — 있으면 하나. 한 슬롯에 최대 하나(모양으로 보장). |

`current_value`는 네 갈래 중 하나다.

| 표기 | 뜻 |
|---|---|
| `{ "answer": <Value> }` | 확정한 답. Value는 선택지 문자열 또는 `{amount, unit}`. |
| `"UNKNOWN_RECORD"` | 모름으로 기록 |
| `"REFUSAL_RECORD"` | 거절로 기록 |
| `"NONE"` | 아직 없음(초기값·무효화 뒤) |

- `history`에는 **답이었던 값만** 쌓는다. 모름·거절은 답이 아니므로 이력에 쌓지 않는다.
- `pending`(확인 대기)은 슬롯당 최대 하나이고, `pending_id`는 확인 대기를 둘 때마다 새로 만든다(이전 확인의 “네”가 새 값을 받아들이지 않도록).
- `risk_mark`는 현재값이 슬롯의 위험 기준에 해당할 때의 대응이다. 위험 표시는 현재값(또는 확인 대기 값)에 붙어 움직인다.

### 2.2 진행 기록(`ProgressRecord`) — Plan만 쓴다

| 필드 | 타입 | 뜻 |
|---|---|---|
| `last_directive` | Directive \| null | **직전 응답 지시** — 마지막 턴의 응답 지시. 처음이면 없음. |
| `open_requests` | OpenRequests | **열린 요청** — 열린 요청. |
| `skipped` | array<SkipEntry> | **건너뜀** — 건너뛴 문항들. |
| `confirm_stopped` | array<SlotRef> | **확인 중단** — 확인을 그만둔 슬롯들. 확인 대기는 남는다. |
| `session_status` | SessionStatus | **세션 상태** — 세션 상태. |
| `pause_history` | array<PauseEntry> | **중지 이력** — 일시 중지·재개 기록. |

`open_requests`(열린 요청)는 사용자가 요구했고 아직 풀리지 않은 **사실**이다(정정 요청·중단 요청·미룸).

| 필드 | 타입 | 뜻 |
|---|---|---|
| `correction_requests` | array<object> | **정정 요청** — 값을 아직 받지 못한 고칠 요청. |
| `stop_requested` | boolean | **중단 요청** — 그만하겠다고 했고 아직 확인하지 않음. |
| `deferred` | array<object> | **미룸** — 나중에 묻기로 한 것. |

### 2.3 Plan 기록(`PlannerRecord`) — Plan만 쓰고 읽는다

사실로 다시 계산할 수 없는 **횟수**만 둔다.

| 필드 | 타입 | 뜻 |
|---|---|---|
| `attempt_counts` | array<object> | **시도 횟수** — 문항마다 쓸 수 있는 답 없이 지나간 턴 수(8-2절). |
| `confirm_counts` | array<object> | **확인 횟수** — 슬롯마다 확인 대기 확인을 낸 횟수(반복 요청으로 다시 낸 것 제외, 대체돼도 이어 셈). |
| `unknown_counts` | array<object> | **모름 횟수** — 문항마다 모름 판정이 나온 턴 수. |
| `refusal_counts` | array<object> | **거절 횟수** — 문항마다 거절 판정이 나온 턴 수. |
| `unrecognized_streak` | integer(0..1000) | **알아듣지 못한 연속** — 결과가 알아듣지 못함인 턴이 이어진 수. 응답 있음·무관만이면 0, 요청만이면 그대로. |
| `ask_counts` | array<object> | **물은 횟수** — 정정 요청·미룸·종료 확인·중단 확인을 풀리지 않은 채 물은 횟수. |

### 2.4 세션 정보 · 대화 로그 · 전달 기록

**`SessionInfo`** — 세션 정보: 세션 식별과 문항 정의 버전.

| 필드 | 타입 | 뜻 |
|---|---|---|
| `session_id` | SessionId | **세션 식별** — 어느 세션의 값인지. |
| `question_bank_version` | integer(0..1000) | **문항 정의 버전** — 세션을 만들 때의 최신 버전. |

**`LogEntry`** — 대화 로그 항목: 턴마다 한 건. 이번 턴에 오간 경계 값을 판단 없이 모은 것.

| 필드 | 타입 | 뜻 |
|---|---|---|
| `input` | object | **입력** — 이번 턴 입력. |
| `handling` | object \| `IGNORED` | **처리** — 처리 표의 결과. |
| `question_bank_version` | integer(0..1000) | **문항 정의 버전** — 이 턴에 쓴 버전. |
| `turn_result` | `COMMITTED` \| `NOT_APPLICABLE` \| object | **턴 결과** — 확정 / 실패(단계들) / 해당 없음(처리 안 함). |
| `parser_output` | ParserOutput \| null | **LoRA-A 출력** — 이번 턴에 만들어진 것만. 없으면 없음. |
| `normalizer_output` | NormalizerOutput \| null | **정규화·검증 출력** — 이번 턴 정규화·검증 컴포넌트의 검증된 출력. 출력 생성 전 실패하거나 수행하지 않았으면 null. |
| `judge_output` | JudgeOutput \| null | **상태 판정 출력** — 이번 턴 상태 판정 컴포넌트의 검증된 출력. 출력 생성 전 실패하거나 수행하지 않았으면 null. |
| `record_writer_output` | StoreResult \| null | **저장 판단 출력** — 이번 턴 저장 판단 컴포넌트의 검증된 출력. 결정이 실제 확정됐는지는 턴 결과·실패 시점으로 구분한다. |
| `directive` | Directive \| null | **응답 지시** — 이번 턴 Plan이 만든 응답 지시. 생성되지 않았으면 null. 응답 생성·전달의 성공을 뜻하지 않는다. |
| `flow` | Flow \| null | **흐름** — 이번 턴 Plan이 낸 CONTINUE 또는 END. Plan 출력이 없으면 null. 후속 전달 성공과는 별개다. |
| `progress_record_update` | ProgressRecordUpdate \| null | **진행 기록 갱신** — 이번 턴 Plan이 만든 진행 기록 갱신안. 실제 반영 여부는 쓰기 확정 결과와 함께 확인한다. |
| `staff_alert` | StaffAlert \| null | **직원 알림** — 이번 턴 Plan이 만든 직원 알림. 알림이 없거나 Plan을 만들지 못했으면 null. 전달 성패는 staff_alert_delivery로 확인한다. |
| `response_text` | string(≤2000) \| null | **응답 문장** — 생성해 프론트에 전달하려고 한 응답 문장. 전달 실패 시 실제 청취는 보장되지 않는다. |
| `staff_alert_delivery` | `SUCCESS` \| `FAILURE` \| `NOT_APPLICABLE` | **직원 알림 전달** — LangGraph가 알림을 전달한 결과. |
| `turn_failure_signal` | TurnFailureSignal \| null | **턴 실패 신호** — 낸 것. 없으면 없음. |
| `intervention_result` | InterventionResult \| null | **개입 결정 결과** — 낸 것. 없으면 없음. |

**`DispatchRecord`** — 전달 기록: 결과 전달 한 건.

| 필드 | 타입 | 뜻 |
|---|---|---|
| `succeeded` | boolean | **성공 여부** — 성공했는지. |

## 3. 쓰기 — 저장 결정이 기록에 주는 효과

저장 판단(Record Writer)은 판정을 슬롯별 **저장 결정**(`StoreDecision`: 슬롯 · 동작 · 값 · 확인 대기 ID · 위험 표시)으로 펼친다. 기록 저장소는 판단 없이 아래 효과만 반영한다.

| 동작 | 현재값 | 이력 | 확인 대기 | 위험 표시 | 쓰이는 경우 |
|---|---|---|---|---|---|
| `FIRST_WRITE` 첫 저장 | 답(값) | 그대로 | 그대로 | 받은 것 | 빈 슬롯에 첫 답 (B1) |
| `NEW_REVISION` 새 revision | 답(값) | 이전 답이 있으면 추가 | 그대로 | 받은 것 | 정정 (C1) |
| `RECORD_UNKNOWN` 모름 기록 | 모름 | 이전 답이 있으면 추가 | 그대로 | 없음 | 모름 (B7) |
| `RECORD_REFUSAL` 거절 기록 | 거절 | 이전 답이 있으면 추가 | 그대로 | 없음 | 거절 (B8) |
| `SET_PENDING` 확인 대기 둠 | 그대로 | 그대로 | {ID, 값, 위험 표시}(있던 것은 대체) | 그대로 | 충돌 — 기존 값을 지킨다 (C3) |
| `ACCEPT_PENDING` 확인 대기 받아들임 | 답(확인 대기 값) | 이전 답이 있으면 추가 | 없음 | 확인 대기의 것 | 확인 질문에 “네” (C4) |
| `DROP_PENDING` 확인 대기 버림 | 그대로 | 그대로 | 없음 | 그대로 | 확인 질문에 “아니요” 등 (C4) |
| `INVALIDATE` 무효화 | 없음 | 이전 답이 있으면 추가 | 없음 | 없음 | 선행 답이 바뀌어 후속 답이 맞지 않게 됨 (C2) |

저장 결정 규칙(`record_writer.md` 7절 요약):

- 정상(첫 답) → `FIRST_WRITE`, 정상(같은 값) → 없음(확인 대기 버림만), 정정 → `NEW_REVISION`(받아들임이면 `ACCEPT_PENDING`), 충돌 → `SET_PENDING`, 모름·거절 → `RECORD_*`.
- 애매·누락·선행 불충족은 **저장하지 않는다**. 변경 없는 슬롯은 내지 않는다.
- 무효화는 **먼저** 낸다(같은 턴에 다시 받은 값이 지워지지 않게). 기록이 없는 슬롯에는 내지 않는다.
- 판정의 확인 대기 처리가 “버림”인데 그 동작이 확인 대기를 지우지 않는 동작(`RECORD_*`·`NEW_REVISION`)이면 같은 슬롯에 `DROP_PENDING`을 그 뒤에 하나 더 낸다. 한 슬롯에 결정이 둘인 경우는 이것뿐이다.
- 문항 전체 판정은 그 문항의 모든 슬롯으로 펼친다(상태 판정이 뺀 슬롯 제외).

### 3.1 진행 기록 갱신 연산 (`ProgressRecordUpdate` → `ProgressRecord`)

| 갱신 필드 | 효과 |
|---|---|
| `last_directive` | 직전 응답 지시를 **교체**한다. |
| `open_requests` | **통째로 교체**한다. |
| `skipped_add` | 같은 문항이 있으면 사유를 교체, 없으면 추가한다. |
| `skipped_remove` | 건너뜀에서 뺀다. 추가와 해제가 함께면 **해제 먼저**. |
| `confirm_stopped_add` / `_remove` | 추가 / 뺀다. |
| `session_status` | 값이 오면 교체(없으면 그대로). |
| `pause_history_add` | 끝에 추가한다. |
| (`PlannerOutput.planner_record_update`) | Plan 기록을 **통째로 교체**한다. |

### 3.2 세션을 처음 만들 때의 초기값

세션 정보를 만들고(LangGraph가 정하는 유일한 초기값), 나머지는 다음과 같다.

```json
{
  "answer_records": "모든 슬롯 current_value=\"NONE\", history=[], pending=null, risk_mark=null",
  "progress_record": {
    "last_directive": null,
    "open_requests": {
      "correction_requests": [],
      "stop_requested": false,
      "deferred": []
    },
    "skipped": [],
    "confirm_stopped": [],
    "session_status": "IN_PROGRESS",
    "pause_history": []
  },
  "planner_record": {
    "attempt_counts": [],
    "confirm_counts": [],
    "unknown_counts": [],
    "refusal_counts": [],
    "unrecognized_streak": 0,
    "ask_counts": []
  },
  "dialogue_log": [],
  "dispatch_log": []
}
```

## 4. 한 턴의 쓰기 순서와 실패

| 순서 | 쓰기 | 쓰는 쪽 | 묶음 |
|---|---|---|---|
| 1 (턴 맨 앞) | 세션 정보 생성 | LangGraph | 따로 쓴다. 실패하면 붙일 세션이 없어 로그도 남기지 않는다. |
| 2 | 저장 결정(`answer_records`) + 진행 기록 갱신 + Plan 기록 갱신 | 저장 판단 · Plan | **함께 확정**. 중간에 실패하면 모두 반영되지 않는다. |
| 3 (확정 뒤) | 전달 기록 | 결과 전달 | 확정 뒤, 서로의 성패와 무관. 전달이 실패해도 `succeeded=false`로 남는다(J5). |
| 4 (턴 맨 끝) | 대화 로그 | LangGraph | 따로 쓴다. 실패한 턴도 남긴다(실패 단계 포함). |

- 쓰기 확정 자체가 실패하면 확정 뒤의 일(직원 알림·응답 생성·프론트 전달·결과 전달)은 하나도 하지 않고, 턴 실패 신호의 `write_committed=NOT_COMMITTED`로 알린다. 같은 말을 다시 하면 처음처럼 처리된다.
- 쓰기는 반영됐는데 응답만 못 나간 경우 `write_committed=COMMITTED`이고 사용자는 반복 요청으로 같은 말을 다시 들을 수 있다.
- 같은 세션의 턴은 한 번에 하나씩 처리하므로, “턴 시작” 값은 지난 턴의 쓰기를 모두 반영한 값이다.
- 대화 로그를 남기지 않는 경우: 세션 없음 열의 처리 안 함, 세션 정보 생성에 실패한 턴, 종료 열의 처리 안 함. 일시 중지 열의 처리 안 함은 남긴다.

## 5. 읽기 — 컴포넌트별로 가져가는 범위와 시점

| 읽는 컴포넌트 | 입력 필드 | 저장소 필드 | 시점 |
|---|---|---|---|
| 사람 개입 | `StaffConsoleInput.staff_alert` | 기록 저장소.session_info.session_id | 이번 턴(앞 단계 출력) |
| LangGraph | `OrchestratorInput.session_found` | 기록 저장소.session_info.session_id | 턴 맨 앞 |
| LangGraph | `OrchestratorInput.session_question_bank_version` | 기록 저장소.session_info.question_bank_version | 턴 시작 |
| LangGraph | `OrchestratorInput.session_status` | 기록 저장소.progress_record.session_status | 턴 시작 |
| LangGraph | `OrchestratorInput.latest_question_bank_version` | 문항 정의 저장소.version | 항상 같음(읽기 전용) |
| LoRA-A | `UtteranceParserInput.last_directive` | 기록 저장소.progress_record.last_directive | 턴 시작 |
| LoRA-A | `UtteranceParserInput.awaiting_questions` | 문항 정의 저장소.questions | 항상 같음(읽기 전용) |
| LoRA-A | `UtteranceParserInput.question_names` | 문항 정의 저장소.questions | 항상 같음(읽기 전용) |
| LoRA-A | `UtteranceParserInput.answered_slots` | 기록 저장소.answer_records | 턴 시작 |
| LoRA-A | `UtteranceParserInput.guide_list` | 문항 정의 저장소.session_settings.guide_list | 항상 같음(읽기 전용) |
| 정규화·검증 | `AnswerNormalizerInput.related_questions` | 문항 정의 저장소.questions | 항상 같음(읽기 전용) |
| 정규화·검증 | `AnswerNormalizerInput.current_values` | 기록 저장소.answer_records | 턴 시작 |
| 정규화·검증 | `AnswerNormalizerInput.pendings` | 기록 저장소.answer_records | 턴 시작 |
| 정규화·검증 | `AnswerNormalizerInput.awaiting` | 기록 저장소.progress_record.last_directive | 턴 시작 |
| 상태 판정 | `AnswerJudgeInput.risk_phrases` | 문항 정의 저장소.session_settings.risk_phrases | 항상 같음(읽기 전용) |
| 상태 판정 | `AnswerJudgeInput.last_directive` | 기록 저장소.progress_record.last_directive | 턴 시작 |
| 상태 판정 | `AnswerJudgeInput.pendings` | 기록 저장소.answer_records | 턴 시작 |
| 상태 판정 | `AnswerJudgeInput.affected_followups` | 문항 정의 저장소.questions | 항상 같음(읽기 전용) |
| 상태 판정 | `AnswerJudgeInput.question_slots` | 문항 정의 저장소.questions | 항상 같음(읽기 전용) |
| 저장 판단 | `RecordWriterInput.question_slots` | 문항 정의 저장소.questions | 항상 같음(읽기 전용) |
| 저장 판단 | `RecordWriterInput.target_records` | 기록 저장소.answer_records | 턴 시작 |
| Plan 결정 | `DialoguePlannerInput.answer_records` | 기록 저장소.answer_records | 저장 결정 반영 뒤 |
| Plan 결정 | `DialoguePlannerInput.last_directive` | 기록 저장소.progress_record.last_directive | 턴 시작 |
| Plan 결정 | `DialoguePlannerInput.skipped` | 기록 저장소.progress_record.skipped | 턴 시작 |
| Plan 결정 | `DialoguePlannerInput.confirm_stopped` | 기록 저장소.progress_record.confirm_stopped | 턴 시작 |
| Plan 결정 | `DialoguePlannerInput.open_requests` | 기록 저장소.progress_record.open_requests | 턴 시작 |
| Plan 결정 | `DialoguePlannerInput.planner_record` | 기록 저장소.planner_record | 턴 시작 |
| Plan 결정 | `DialoguePlannerInput.question_bank` | 문항 정의 저장소.(전체) | 항상 같음(읽기 전용) |
| 결과 전달 | `DispatchInput.session_info` | 기록 저장소.session_info | 턴 쓰기 반영 뒤 |
| 결과 전달 | `DispatchInput.answer_records` | 기록 저장소.answer_records | 턴 쓰기 반영 뒤 |
| 결과 전달 | `DispatchInput.skipped` | 기록 저장소.progress_record.skipped | 턴 쓰기 반영 뒤 |
| 결과 전달 | `DispatchInput.confirm_stopped` | 기록 저장소.progress_record.confirm_stopped | 턴 쓰기 반영 뒤 |
| 결과 전달 | `DispatchInput.session_status` | 기록 저장소.progress_record.session_status | 턴 쓰기 반영 뒤 |
| 결과 전달 | `DispatchInput.pause_history` | 기록 저장소.progress_record.pause_history | 턴 쓰기 반영 뒤 |

저장소에서 일부만 가져오는 입력(`answered_slots`, `current_values`, `pendings`, `target_records`, `related_questions` 등)은 판단 없는 **고르기**만 허용한다. 범위 고르기에 판단이 섞이면 그 판단이 계약 밖에 숨기 때문이다.

## 6. 문항 정의 저장소(`QuestionBank`)

| 필드 | 타입 | 뜻 |
|---|---|---|
| `version` | integer(0..1000) | **버전** — 버전 번호. |
| `questions` | array<QuestionDef> | **문항** — 문항들. |
| `session_settings` | SessionSettings | **세션 설정** — 설정. |

**`QuestionDef`** — 문항 정의: 문항 하나.

| 필드 | 타입 | 뜻 |
|---|---|---|
| `question_id` | QuestionId | **문항 ID** — 식별자. |
| `name` | string(≤2000) | **이름** — 말할 때 쓰는 이름. |
| `order` | integer(0..1000) | **순서** — 묻는 순서. |
| `prerequisite` | Prerequisite \| null | **선행 조건** — 없으면 항상 묻는다. |
| `question_sentence` | string(≤2000) | **문항 문장** — 물을 때의 문장. |
| `refusal_explanation` | string(≤2000) | **거절 시 설명** — 왜 묻는지 설명하는 문장. |
| `guide_sentences` | array<QuestionGuideSentence> | **안내 문장** — 문항별 안내 항목마다 하나(등록 규칙: 모든 문항에 있어야 등록). |
| `affected_followups` | array<QuestionId> | **영향받는 후속 문항** — 이 문항 답이 바뀌면 무효가 되는 후속 문항. |
| `policy` | Policy | **정책** — 문항 정책. |
| `repeat_keys` | array<string> | **반복 키** — 이 문항이 줄마다 반복되면 쓸 수 있는 반복 키들. 반복하지 않으면 빈 목록. |
| `slots` | array<SlotDef> | **슬롯** — 답 칸들. |

**`SlotDef`** — 슬롯 정의: 문항의 답 칸 하나.

| 필드 | 타입 | 뜻 |
|---|---|---|
| `slot_id` | string | **슬롯 ID** — 문항 안의 칸 식별자. |
| `units` | array<UnitDef> | **단위** — 단위 슬롯의 단위들. 선택지 슬롯이면 빈 목록. |
| `choices` | array<string(≤2000)> | **선택지** — 선택지 슬롯의 선택지. 단위 슬롯이면 빈 목록. |
| `yes_no_map` | object \| null | **네아니요 대응** — "네"·"아니요"가 이 슬롯의 어떤 선택지인지. 예/아니요로 답할 수 있는 선택 슬롯만. |
| `required` | boolean | **필수** — 꼭 받아야 하는 칸인지. |
| `reask_sentence` | string(≤2000) | **되묻기 문장** — 이 칸만 다시 물을 때의 문장. |
| `risk_rule` | RiskRule \| null | **위험 기준** — 있으면 그 조건과 대응. 없으면 없음. |

**`SessionSettings`** — 세션 설정: 문항과 상관없는 설정.

| 필드 | 타입 | 뜻 |
|---|---|---|
| `risk_phrases` | array<string(≤2000)> | **위험 표현 목록** — 원문에 들어 있으면 위험 신호로 보는 표현. |
| `confirm_limit` | integer(1..20) | **확인 상한** — 같은 확인 대기를 물을 수 있는 최대 횟수. |
| `unrecognized_streak_limit` | integer(1..20) | **알아듣지 못한 연속 상한** — 이만큼 이어지면 도움 요청. |
| `ask_limit` | integer(1..20) | **물음 상한** — 같은 대상을 풀리지 않은 채 물을 수 있는 최대 횟수. |
| `fixed_sentences` | array<FixedSentence> | **고정 문장** — 행동·알릴 것 종류마다 하나. 의료진이 검토해 등록한다. |
| `guide_list` | array<GuideItem> | **안내 목록** — 안내 항목들. |

**`Policy`** — 문항 정책: 문항마다 몇 번까지 묻는지.

| 필드 | 타입 | 뜻 |
|---|---|---|
| `question_limit` | integer(1..20) | **질문 상한** — 쓸 수 있는 답 없이 이 문항을 물을 수 있는 최대 횟수. |
| `unknown_accept_after` | integer(1..20) | **모름 수용 시점** — 몇 번째 모름에서 받아들이고 넘어가는지(1이면 첫 모름에 넘어감). |
| `refusal_accept_after` | integer(1..20) | **거절 수용 시점** — 몇 번째 거절에서 받아들이고 넘어가는지. |

**`Prerequisite`** — 선행 조건: 이 문항을 묻는 조건: 다른 슬롯의 답이 이 선택지일 때만.

| 필드 | 타입 | 뜻 |
|---|---|---|
| `slot` | SlotRef | **슬롯** — 선행 슬롯. |
| `value` | string(≤2000) | **값** — 이 선택지일 때만 묻는다. |

규칙 본문은 어느 기관의 문항 값도 적지 않는다. 선택지·단위·이름·환산·상한은 전부 문항 정의와 세션 설정(`SessionSettings`)이 정한다. 예시 문항(Q1~Q8)은 [`tests/e2e/fixtures/question_bank.json`](tests/e2e/fixtures/question_bank.json).

## 7. 참조 구현과 검증

`tests/e2e/run_e2e.py`의 `apply_store_decisions` · `apply_progress_update` · `apply_turn`이 위 효과를 코드로 옮긴 **참조 구현**이다. E2E 시나리오는 `db_after_store = apply(db_before, store_decisions)` 와 `db_final = apply(db_before, store_decisions, Plan 갱신)`을 검사한다. 이 코드는 계약을 설명·검증하기 위한 것이며 운영용 DB 어댑터가 아니다. 영속화 방식(RDB·문서 DB 등)과 트랜잭션 구현은 DB Adapter 쪽에서 정하되, §4의 묶음 규칙을 지켜야 한다.
