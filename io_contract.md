# Model I/O Contract (io_contract.md)

> 담당: 송다빈(Model I/O / E2E) · 근거: 스키마 프로젝트(`schema-project`)의 JSON Schema 원본 22개 경계, 업무 규칙 명세, 216개 테스트케이스.  
> 이 문서의 필드표·코드 어휘는 `work/contracts/`의 Schema와 필드 설명에서 **자동 생성**했다. 값의 모양은 [`schemas/`](schemas/)의 JSON Schema가 원본이다.

## 1. 한눈에 보기

**처리 흐름 (작업문서 기준)**

`사용자 입력 → LoRA-A → 정규화·검증 → DB 저장 → Transition Plan → LangGraph → LoRA-B → 사용자 응답`

**스키마상의 컴포넌트 12개** — 모델 2, 코드 5, 흐름 제어 1, 외부 접점 3, 저장소 2(블랙박스: 하는 일·받는 값·내는 값·지켜야 할 규칙만 정한다).

| 컴포넌트 | 영문명 | 종류 | 입력 계약 | 출력 계약 | 책임 |
|---|---|---|---|---|---|
| 프론트 | Frontend | 외부 접점 | `FrontendInput` | `FrontendMessage` | 사용자 말을 STT로 글자로 바꿔 보내고, 응답 문장을 TTS로 읽어 준다. |
| 사람 개입 | Staff Console | 외부 접점 | `StaffConsoleInput` | `InterventionDecision` | 직원·의료진에게 알림을 보여 주고, 그들의 결정(재개·종료)을 보낸다. |
| LangGraph | Orchestrator | 흐름 제어 | `OrchestratorInput` | `OrchestratorOutput` | 한 턴의 순서대로 컴포넌트를 부르고, 저장소에서 정해진 범위를 가져와 건네고, 쓰기를 저장소에 전달한다. |
| LoRA-A | Utterance Parser | 모델 | `UtteranceParserInput` | `ParserOutput` | 사용자 발화를 (대상, 값, 원문, 의도) 항목들로 바꾼다. |
| 정규화·검증 | Answer Normalizer | 코드 | `AnswerNormalizerInput` | `NormalizerOutput` | 항목 값을 표준 형태로 바꾸고, 규칙 위반·기존 값과의 같음/다름·빠진 필수 슬롯·선행 조건을 사실로 표시한다. |
| 상태 판정 | Answer Judge | 코드 | `AnswerJudgeInput` | `JudgeOutput` | 이번 발화가 각 대상에 대해 무엇을 뜻하는지(정상·정정·충돌·누락 등) 판정한다. |
| 저장 판단 | Record Writer | 코드 | `RecordWriterInput` | `StoreResult` | 판정을 응답 기록에 어떻게 반영할지 슬롯별로 정한다. |
| Plan 결정 | Dialogue Planner | 코드 | `DialoguePlannerInput` | `PlannerOutput` | 다음에 무엇을 말할지 정하고, 그 말에 필요한 값과 문장 재료를 담은 응답 지시를 만든다. |
| LoRA-B | Response Generator | 모델 | `ResponseGeneratorInput` | `GeneratorOutput` | 응답 지시를 사용자 발화에 맞춰 받아 주며 자연스러운 문장으로 바꾼다. |
| 결과 전달 | Result Dispatcher | 외부 접점(붙을 예정) | `DispatchInput` | `DispatchOutput` | 확정된 문진 결과를 시스템 밖으로 넘긴다. |
| 문항 정의 저장소 | Question Bank | 저장소 | `QuestionBank` | — | 문진 설계자가 등록한 문항 정의를 버전별로 읽기 전용으로 보관한다. |
| 기록 저장소 | Session Store | 저장소 | `SessionStore` | — | 세션별 응답 기록·진행 기록·Plan 기록·세션 정보·로그를 보관하고, 받은 쓰기를 정해진 효과대로 반영한다. |

**원칙 (스키마 프로젝트 `rules/principles.md` 요약)**

- 모든 컴포넌트는 블랙박스다. 안쪽을 바꿔도 다른 컴포넌트의 받는 값·내는 값은 바뀌지 않아야 한다(LoRA-A/B 교체 가능).
- 받는 값의 출처는 **이번 턴의 다른 컴포넌트 출력** 또는 **저장소 필드** 둘뿐이다. 저장소에서 일부만 가져오면 범위를 적는다(판단 없는 고르기만).
- 외부(사람) 값은 프론트(사용자) · 사람 개입(직원) · 문항 정의 저장소(문진 설계자) 세 곳으로만 들어온다.
- 저장소 필드마다 쓰는 쪽은 하나다. 저장소는 판단하지 않고 받은 쓰기를 정해진 효과대로만 반영한다.
- 다음에 물을 것은 저장하지 않는다. 저장하는 것은 사실(응답 기록·건너뜀·확인 중단·열린 요청·횟수)뿐이고 매 턴 다시 계산한다.
- 각 컴포넌트는 출력이 자신의 계약을 지키는 것까지 책임지고, 못 지킬 때의 대체 출력을 정해 둔다(J7). LangGraph는 검증한 경계값을 다음 컴포넌트로 넘긴다.

## 2. 작업문서 용어와 계약의 대응

작업문서(업무분담 및 구현 계획)의 7단계·계약 이름이 스키마에서는 아래처럼 나뉘어 있다. **이름이 다르거나 쪼개진 곳**이 있으므로 구현할 때 이 표로 맞춘다.

| 작업문서 | 스키마의 컴포넌트·계약 | 비고 |
|---|---|---|
| ① 사용자 입력 (자연어 발화 원문) | 프론트 → `FrontendMessage` (`kind`: SESSION_START / UTTERANCE / SESSION_END) | 직원 결정은 `InterventionDecision`(RESUME / END)으로 따로 들어온다. |
| ② LoRA-A Input: `session_id` / `question_id` / `question_schema` / `user_utterance` / `relevant_state` | `UtteranceParserInput`: `utterance` · `last_directive`(직전 응답 지시) · `awaiting_questions`(= question_schema, 기다리는 문항 정의) · `question_names` · `answered_slots`(= relevant_state) · `guide_list` | `session_id`는 모델 입력에 넣지 않는다(모델은 세션을 모른다). `question_id`는 `last_directive.awaiting.targets`로 전달된다. 최근 대화 전체는 넣지 않는다(현재 1턴 + 필요한 상태만). |
| ② LoRA-A Output: `facts` / `intents` / `relations` / `unmapped_facts` | `ParserOutput.items[]`: `target` · `value` · `source_text` · `intent` · `progress_op` · `guide_id` | fact = (target, value, source_text). intents = `intent`. relations(정정·확인) = 의도 `CORRECTION_MARKED` / `CONFIRM_YES` / `CONFIRM_NO`. unmapped_facts = 의도 `OUT_OF_SCOPE` / `UNRECOGNIZED`(대상 없음). 저장 여부·다음 질문·최종 문장은 정하지 않는다. |
| ③ 정규화·검증 Output: `normalized_values` / `semantic_status` / `issues` / `persist` / `transition_plan` | **네 컴포넌트로 나뉜다.** 정규화·검증 `NormalizerOutput`(표준 값 `standard_value`, 문제 `problems`) → 상태 판정 `JudgeOutput`(상태 `status`) → 저장 판단 `StoreResult`(저장 결정 = persist) → Plan `PlannerOutput`(`directive` = transition_plan) | 작업문서는 정규화·검증 한 덩어리에 상태 판정·분기까지 담았다. 스키마는 값 규칙(정규화)·해석 규칙(판정)·저장 규칙·대화 정책을 따로 바꿀 수 있게 분리했다. |
| ④ DB 저장 (현재값·수정 이력·진행 상태) | 저장 판단 `StoreResult` → 기록 저장소 `SessionStore`: `answer_records[].current_value / history / pending`, `progress_record`, `planner_record` | 자세한 내용은 [db_contract.md](db_contract.md). |
| ⑤ 행동 결정 → Transition Plan | Plan `PlannerOutput.directive` (`action`, `targets`, `say_values`, `notices`, `sentence_materials`) + `flow` + `staff_alert` + 기록 갱신 | 작업문서의 Plan 이름(NEXT 등)은 아래 §2.1 표 참고. |
| ⑥ LangGraph Conditional Edge | Orchestrator: 처리 표(입력 종류 × 세션 상태) · 흐름 종료 · 턴 실패 | **작업문서와 다른 점**: 작업문서는 9개 상태로 Conditional Edge 분기를 하지만, 스키마는 판정 상태·행동 종류로 분기하지 않는다(행동 하나를 바꿀 때 Plan·LangGraph·LoRA-B 세 곳을 고치지 않도록). |
| ⑦ LoRA-B Input: `question_id` / `normalization_result` / `transition_plan` / `next_question` | `ResponseGeneratorInput`: `directive`(응답 지시) · `utterance` | 정규화 결과·다음 문항 정보는 응답 지시 안에 이미 들어 있다(`say_values`, `sentence_materials.question_sentences`). |
| ⑦ LoRA-B Output: `response_text` | `GeneratorOutput`: `response_text` · `is_fallback` | 새 설문 값·상태를 지어내지 않는다. 지키지 못하면 문장 재료를 그대로 읽는 대체 출력. |

### 2.1 코드 상태·Plan 이름 대응 (신민지 담당 분기표 ↔ 스키마 코드)

| 작업문서 상황 | 작업문서 Code 상태 | 스키마 판정/의도 | 작업문서 Plan | 스키마 Plan 행동 · 알릴 것 | DB 처리 (저장 동작) |
|---|---|---|---|---|---|
| 정상 응답 | ANSWERED | 판정 `ANSWERED` | NEXT | `ASK_NEXT` (또는 마칠 때 `ASK_FINISH`) | `FIRST_WRITE` |
| 필수 정보 누락 | MISSING | 판정 `MISSING` | ASK_MISSING | `ASK_MISSING` | 받은 슬롯만 저장, 빠진 슬롯은 저장 안 함 |
| 애매한 범위·표현 | UNCLEAR | 판정 `UNCLEAR` (사유 `AMBIGUOUS` / `NO_UNIT` / `OUT_OF_RANGE` …) | ASK_CLARIFICATION | `ASK_CLARIFY` | 저장 안 함(미확정) |
| 기존 값과 충돌 | CONFLICT | 판정 `CONFLICT` | ASK_CONFLICT | `ASK_CONFIRM` (확인 대기 확인) | `SET_PENDING` — 기존 확정값 유지, 새 값은 확인 대기 |
| 사용자 정정 | CORRECTION | 판정 `CORRECTION` (의도 `CORRECTION_MARKED`) | ACK_CORRECTION | 알릴 것 `CORRECTION_ACK` + 다음 행동 | `NEW_REVISION` — 이전 값은 이력으로 |
| 모름 | UNKNOWN | 판정 `UNKNOWN` (의도 `SAYS_UNKNOWN`) | ASK_OR_HOLD | `ASK_AFTER_UNKNOWN`, 수용 시점이면 건너뜀(`UNKNOWN_ACCEPTED`) 후 다음 문항 | `RECORD_UNKNOWN` |
| 답변 거부 | REJECTED | 판정 `REJECTED` (의도 `SAYS_REFUSAL`) | HOLD_OR_SKIP | `ASK_AFTER_REFUSAL`, 수용 시점이면 건너뜀(`REFUSAL_ACCEPTED`) | `RECORD_REFUSAL` |
| 문진 무관 응답 | OOS | **판정이 아니라** 의도 `OUT_OF_SCOPE` → 발화 판정 `OUT_OF_SCOPE_ONLY` | REDIRECT | `REDIRECT` | 저장 안 함 |
| 문진 완료 | COMPLETE | **판정이 아니라** 흐름: `ASK_FINISH` → 승낙(`CONFIRM_YES`) → `FAREWELL` + `flow=END` + 세션 `ENDED_COMPLETE` | COMPLETE | `ASK_FINISH` → `FAREWELL` | 결과 전달(Finalization 기록 = 전달 기록) |

작업문서에 없지만 스키마에는 있는 것: 판정 `PREREQUISITE_UNMET`(선행 불충족), 행동 `RISK_NOTICE`·`STAFF_NOTICE`·`CALL_STAFF`·`WAIT_NOTICE`·`ASK_REPEAT`·`ASK_STOP`·`ASK_CORRECTION_TARGET`, 의도 `RISK_SIGNAL`·`USER_CALLED_STAFF`·`PROGRESS_OP`·`GUIDE_REQUEST`. 모두 테스트케이스(G·F·D·E·I 계열)가 요구한 것이다.

## 3. 시점별로 어떤 컴포넌트가 쓰이나

### 3.0 턴 종류와 호출 컴포넌트

Orchestrator의 처리 표(9-1절)가 입력 종류 × 세션 상태로 턴 종류를 정한다. “처리 안 함”은 어떤 컴포넌트도 부르지 않고 응답도 없다.

| 입력 \ 세션 상태 | 세션 없음 | 진행 중 | 일시 중지(위험) | 종료 |
|---|---|---|---|---|
| 세션 시작 신호 | 세션 정보 생성 후 Plan(`SESSION_START`) | Plan(`SESSION_START`) | 처리 안 함 | 처리 안 함 |
| 발화 | 세션 정보 생성 후 전체 흐름(`UTTERANCE`) | 전체 흐름(`UTTERANCE`) | 처리 안 함(로그는 남김) | 처리 안 함(로그 없음) |
| 개입 결정: 재개 | 처리 안 함 | 처리 안 함 | Plan(`RESUME`) | 처리 안 함 |
| 개입 결정: 종료 | 처리 안 함 | Plan(`INTERVENTION_END`) | Plan(`INTERVENTION_END`) | 처리 안 함 |
| 세션 종료 신호 | 처리 안 함 | Plan(`END_LEFT`) | Plan(`END_LEFT`) | 처리 안 함 |

| 컴포넌트 | 대화 시작 | 발화 | 직원 재개 | 직원 종료 | 이탈 종료 |
|---|---|---|---|---|---|
| 프론트 | ● | ● | ● | ● | ● |
| 사람 개입 | · | △ | ● | ● | · |
| LangGraph | ● | ● | ● | ● | ● |
| LoRA-A | · | ● | · | · | · |
| 정규화·검증 | · | ● | · | · | · |
| 상태 판정 | · | ● | · | · | · |
| 저장 판단 | · | ● | · | · | · |
| Plan 결정 | ● | ● | ● | ● | ● |
| LoRA-B | ● | ● | ● | ● | ● |
| 결과 전달 | · | △ | · | ● | ● |
| 문항 정의 저장소 | ● | ● | ● | ● | ● |
| 기록 저장소 | ● | ● | ● | ● | ● |

● 사용 · △ 조건부(발화 턴에서 위험 신호·사람 요청·도움 요청이면 사람 개입, 종료 확인 승낙이면 결과 전달) · · 사용 안 함. 모든 턴에서 응답이 나가면 프론트가 TTS로 읽는다. 턴 실패 신호는 프론트와 사람 개입으로 간다.

### 3.1 시점별 호출 순서

**대화 시작** — 키오스크 앞에서 말 없이 시작하거나, 연결이 끊겼다 다시 붙을 때(A1·A3).  
발화가 없으므로 LoRA-A~저장 판단을 건너뛴다. 세션이 없으면 만들고, 첫 질문(재접속이면 하던 질문)을 Plan부터 시작한다.

1. 프론트가 세션 시작 신호를 보낸다.  `P1`
2. 세션이 있는지(턴 맨 앞), 세션 상태·문항 버전(턴 시작), 최신 문항 버전을 읽는다.  `R1 Q1`
3. (조건부) 세션이 없으면 세션 정보를 만든다(초기값: 응답 기록 비움, 진행 중).  `W1`
4. 턴 종류 SESSION_START를 Plan으로 보낸다. LoRA-A·정규화·판정·저장 판단은 건너뛴다.  `P3`
5. Plan이 기록(턴 시작)과 문항 정의 전체를 읽어 “지금 물을 것”을 계산한다.  `R6 Q6`
6. Plan이 진행 기록(직전 응답 지시)·Plan 기록을 갱신한다.  `W3`
7. 응답 지시(ASK_NEXT)를 LoRA-B로 보낸다. 발화가 없어 utterance는 null.  `P11`
8. LoRA-B가 첫 질문 문장을 만들어 프론트로 보낸다.  `P13`
9. 턴 끝에 대화 로그를 남긴다.  `W1`

**발화** — 사용자가 말했고 세션이 진행 중일 때(세션이 없으면 만들고 같은 흐름).  
모든 컴포넌트가 순서대로 돈다. 저장 결정이 반영된 뒤의 기록으로 Plan이 다음 말을 정한다.

1. 프론트가 발화 텍스트를 보낸다.  `P1`
2. 세션 존재·상태·문항 버전을 읽는다. 세션이 없으면 세션 정보를 만들고(W1) 같은 흐름으로 간다.  `R1 Q1`
3. (조건부) 세션이 없었다면 세션 정보를 만든다.  `W1`
4. LoRA-A 입력 조립: 발화 + 직전 응답 지시 + 기다리는 문항 정의 + 답한 슬롯 + 안내 목록.  `P4 R2 Q2`
5. LoRA-A 항목 목록을 정규화·검증으로. 현재값·확인 대기·기다리는 답·관련 문항 정의를 함께 받는다.  `P5 R3 Q3`
6. 검사 결과·빠진 필수 슬롯이 상태 판정으로. 항목·발화·위험 표현·직전 응답 지시·확인 대기를 함께 받는다.  `P7 P6 R4 Q4`
7. 판정과 무효화 대상 문항이 저장 판단으로. 기록 대상 슬롯의 현재값을 읽는다.  `P8 R5 Q5`
8. 저장 결정을 기록 저장소에 쓴다(진행·Plan 기록 갱신과 함께 확정).  `W2`
9. Plan 입력 조립: 턴 종류·판정·발화 판정·저장 결과 요약 + 저장 반영 뒤 응답 기록 + 진행/Plan 기록 + 문항 정의.  `P3 P9 P10 R6 Q6`
10. Plan이 진행 기록·Plan 기록을 갱신한다.  `W3`
11. (조건부) 위험 신호·사람 요청·도움 요청이면 직원 알림이 사람 개입으로 간다.  `P12`
12. 응답 지시를 LoRA-B로 보낸다(발화도 함께).  `P11`
13. LoRA-B가 만든 응답 문장이 프론트로 간다.  `P13`
14. (조건부) 흐름이 END(종료 확인 승낙 등)이면 결과 전달을 부르고, 확정된 기록을 넘기고 전달 기록을 남긴다.  `P17 P16 R7 W4`
15. 턴 끝에 대화 로그를 남긴다.  `W1`

**직원 재개** — 위험으로 일시 중지된 세션을 직원·의료진이 재개할 때(G6).  
세션 상태가 “일시 중지(위험)”일 때만 뜻이 있다. LoRA-A~저장 판단 없이 Plan이 재개 안내와 하던 질문을 만든다.

1. 직원 화면이 재개 결정을 보낸다.  `P2`
2. 세션 상태가 PAUSED_RISK인지 확인한다. 아니면 처리하지 않는다.  `R1 Q1`
3. 턴 종류 RESUME을 Plan으로 보낸다.  `P3`
4. Plan이 기록과 문항 정의로 “지금 물을 것”을 계산한다.  `R6 Q6`
5. 세션 상태 IN_PROGRESS, 중지 이력에 재개를 추가한다.  `W3`
6. 알릴 것 RESUME + 지금 물을 것을 LoRA-B로 보낸다.  `P11`
7. 재개 안내와 하던 질문이 프론트로 간다.  `P13`
8. 개입 결정 결과(APPLIED)를 직원 화면에 돌려준다.  `P15`
9. 턴 끝에 대화 로그를 남긴다.  `W1`

**직원 종료** — 직원·의료진이 문진을 끝낼 때(진행 중 또는 일시 중지 상태, F4·G7).  
세션을 종료(미완료: 개입 종료)로 닫고 결과를 넘긴다.

1. 직원 화면이 종료 결정을 보낸다.  `P2`
2. 세션 상태를 읽는다(진행 중 또는 일시 중지만 처리).  `R1 Q1`
3. 턴 종류 INTERVENTION_END를 Plan으로 보낸다.  `P3`
4. Plan이 기록과 문항 정의를 읽는다.  `R6 Q6`
5. 세션 상태 ENDED_STAFF로 기록한다.  `W3`
6. 종료 인사 + 알릴 것 “문진 중단”을 LoRA-B로 보낸다.  `P11`
7. 종료 인사가 프론트로 간다.  `P13`
8. 흐름 END → 결과 전달: 확정된 기록을 넘기고 전달 기록을 남긴다.  `P17 P16 R7 W4`
9. 개입 결정 결과를 직원 화면에 돌려준다.  `P15`
10. 턴 끝에 대화 로그를 남긴다.  `W1`

**이탈 종료** — 프론트가 사용자가 떠났다고 판단할 때(대기 중이어도 같음, A4).  
확인 없이 종료(미완료: 이탈)로 닫고, 받은 데까지의 결과를 넘긴다.

1. 프론트가 세션 종료 신호를 보낸다.  `P1`
2. 세션 상태를 읽는다(진행 중 또는 일시 중지만 처리).  `R1 Q1`
3. 턴 종류 END_LEFT를 Plan으로 보낸다.  `P3`
4. Plan이 기록과 문항 정의를 읽는다.  `R6 Q6`
5. 세션 상태 ENDED_LEFT로 기록한다.  `W3`
6. 종료 인사 + 알릴 것 “문진 중단”.  `P11`
7. LoRA-B 응답 문장이 프론트로 간다.  `P13`
8. 흐름 END → 받은 데까지 결과 전달 + 전달 기록.  `P17 P16 R7 W4`
9. 턴 끝에 대화 로그를 남긴다.  `W1`

**처리 안 함** — 일시 중지 중의 발화(G5), 끝난 세션에 들어온 발화(A5), 세션이 없는데 온 재개·종료 등.  
어떤 컴포넌트도 부르지 않고 응답도 없다. 일시 중지 중의 발화만 대화 로그로 남긴다(직원이 확인할 수 있게).

1. 입력이 들어온다(발화·재개·종료·세션 종료 신호 중 하나).  `P1 P2`
2. 세션 상태를 읽고 처리 표(9-1절)에서 “처리 안 함” 칸임을 확인한다.  `R1`
3. (조건부) 일시 중지 열이면 로그만 남긴다. 세션 없음·종료 열이면 로그도 남기지 않는다.  `W1`

**턴 실패** — 쓰기 확정 실패(J2·J4a), 직원 알림 전달 실패(J3), 응답 생성·전달 실패 등.  
LangGraph가 턴 실패 신호를 프론트와 직원 화면에 보낸다. 쓰기가 확정되지 않았으면 확정 뒤의 일은 하지 않는다.

1. 프론트로 턴 실패 신호(쓰기 확정 여부·직원 알림 결과)를 보낸다. response_text는 없을 수 있다.  `P14`
2. 직원 화면으로도 턴 실패 신호를 보낸다. 개입 결정이었다면 “반영 안 됨(FAILED)” 결과도 보낸다.  `P15`
3. 실패한 턴도 대화 로그는 남긴다(실패 단계 포함).  `W1`

화살표 번호(P·R·Q·W)는 발표용 HTML(`presentation.html`)의 화살표와 같다. 아래 표가 번호의 뜻이다.

| 번호 | 방향 | 종류 | 이름 | 나르는 값 (보내는 쪽 계약.필드) | 받는 쪽 (계약.필드, 읽는 시점) |
|---|---|---|---|---|---|
| P1 | 프론트 → LangGraph | 이번 턴 값 전달 | 프론트 입력 | FrontendMessage | OrchestratorInput.frontend_input |
| P2 | 사람 개입 → LangGraph | 이번 턴 값 전달 | 개입 결정 | InterventionDecision | OrchestratorInput.intervention_decision |
| P3 | LangGraph → Plan 결정 | 이번 턴 값 전달 | 턴 종류 | OrchestratorOutput.turn_kind | DialoguePlannerInput.turn_kind |
| P4 | 프론트 → LoRA-A | 이번 턴 값 전달 | 발화 원문 | FrontendMessage.utterance | UtteranceParserInput.utterance, AnswerJudgeInput.utterance, ResponseGeneratorInput.utterance |
| P5 | LoRA-A → 정규화·검증 | 이번 턴 값 전달 | 항목 목록 | ParserOutput.items | AnswerNormalizerInput.items |
| P6 | LoRA-A → 상태 판정 | 이번 턴 값 전달 | 항목 목록 | ParserOutput.items | AnswerJudgeInput.items |
| P7 | 정규화·검증 → 상태 판정 | 이번 턴 값 전달 | 항목별 검사 | NormalizerOutput | AnswerJudgeInput.item_checks, AnswerJudgeInput.missing_required_slots |
| P8 | 상태 판정 → 저장 판단 | 이번 턴 값 전달 | 판정 | JudgeOutput.judgments, JudgeOutput.invalidated_questions | RecordWriterInput.judgments, RecordWriterInput.invalidated_questions |
| P9 | 상태 판정 → Plan 결정 | 이번 턴 값 전달 | 판정·발화 판정 | JudgeOutput.judgments, JudgeOutput.utterance_judgment | DialoguePlannerInput.judgments, DialoguePlannerInput.utterance_judgment |
| P10 | 저장 판단 → Plan 결정 | 이번 턴 값 전달 | 저장 결과 요약 | StoreResult.store_summary | DialoguePlannerInput.store_summary |
| P11 | Plan 결정 → LoRA-B | 이번 턴 값 전달 | 응답 지시 | PlannerOutput.directive | ResponseGeneratorInput.directive |
| P12 | Plan 결정 → 사람 개입 | 이번 턴 값 전달 | 직원 알림 | PlannerOutput.staff_alert | StaffConsoleInput.staff_alert |
| P13 | LoRA-B → 프론트 | 이번 턴 값 전달 | 응답 문장 | GeneratorOutput.response_text | FrontendInput.response_text |
| P14 | LangGraph → 프론트 | 이번 턴 값 전달 | 턴 실패 신호 | OrchestratorOutput.turn_failure_signal | FrontendInput.turn_failure_signal |
| P15 | LangGraph → 사람 개입 | 이번 턴 값 전달 | 실패 신호·개입 결과 | OrchestratorOutput.turn_failure_signal, OrchestratorOutput.intervention_result | StaffConsoleInput.turn_failure_signal, StaffConsoleInput.intervention_result |
| P16 | LangGraph → 결과 전달 | 제어 신호 | 결과 전달 호출 | OrchestratorOutput.dispatch_called | — |
| P17 | Plan 결정 → LangGraph | 제어 신호 | 흐름(CONTINUE/END) | PlannerOutput.flow | — |
| W1 | LangGraph → 기록 저장소 | 저장소 쓰기 | 세션 생성·대화 로그 | OrchestratorOutput.session_info_created, OrchestratorOutput.log_entry | SessionStore.session_info, SessionStore.dialogue_log |
| W2 | 저장 판단 → 기록 저장소 | 저장소 쓰기 | 저장 결정 | StoreResult.store_decisions | SessionStore.answer_records |
| W3 | Plan 결정 → 기록 저장소 | 저장소 쓰기 | 진행·Plan 기록 갱신 | PlannerOutput.progress_record_update, PlannerOutput.planner_record_update | SessionStore.progress_record, SessionStore.planner_record |
| W4 | 결과 전달 → 기록 저장소 | 저장소 쓰기 | 전달 기록 | DispatchOutput.dispatch_record | SessionStore.dispatch_log |
| Q1 | 문항 정의 저장소 → LangGraph | 저장소 읽기 | 최신 문항 버전 | QuestionBank.version | OrchestratorInput.latest_question_bank_version |
| Q2 | 문항 정의 저장소 → LoRA-A | 저장소 읽기 | 문항·안내 목록 | QuestionBank.questions, QuestionBank.session_settings.guide_list | UtteranceParserInput.awaiting_questions, UtteranceParserInput.question_names, UtteranceParserInput.guide_list |
| Q3 | 문항 정의 저장소 → 정규화·검증 | 저장소 읽기 | 관련 문항 정의 | QuestionBank.questions | AnswerNormalizerInput.related_questions |
| Q4 | 문항 정의 저장소 → 상태 판정 | 저장소 읽기 | 위험 표현·후속 문항 | QuestionBank.session_settings.risk_phrases, QuestionBank.questions | AnswerJudgeInput.risk_phrases, AnswerJudgeInput.affected_followups, AnswerJudgeInput.question_slots |
| Q5 | 문항 정의 저장소 → 저장 판단 | 저장소 읽기 | 문항 슬롯 목록 | QuestionBank.questions | RecordWriterInput.question_slots |
| Q6 | 문항 정의 저장소 → Plan 결정 | 저장소 읽기 | 문항 정의 전체 | QuestionBank | DialoguePlannerInput.question_bank |
| R1 | 기록 저장소 → LangGraph | 저장소 읽기 | 세션 있음·상태·버전 | SessionStore.session_info, SessionStore.progress_record.session_status | OrchestratorInput.session_found (턴 맨 앞), OrchestratorInput.session_question_bank_version (턴 시작), OrchestratorInput.session_status (턴 시작) |
| R2 | 기록 저장소 → LoRA-A | 저장소 읽기 | 직전 지시·답한 슬롯 | SessionStore.progress_record.last_directive, SessionStore.answer_records | UtteranceParserInput.last_directive (턴 시작), UtteranceParserInput.answered_slots (턴 시작) |
| R3 | 기록 저장소 → 정규화·검증 | 저장소 읽기 | 현재값·확인 대기 | SessionStore.answer_records, SessionStore.progress_record.last_directive | AnswerNormalizerInput.current_values (턴 시작), AnswerNormalizerInput.pendings (턴 시작), AnswerNormalizerInput.awaiting (턴 시작) |
| R4 | 기록 저장소 → 상태 판정 | 저장소 읽기 | 직전 지시·확인 대기 | SessionStore.progress_record.last_directive, SessionStore.answer_records | AnswerJudgeInput.last_directive (턴 시작), AnswerJudgeInput.pendings (턴 시작) |
| R5 | 기록 저장소 → 저장 판단 | 저장소 읽기 | 기록 대상 슬롯 | SessionStore.answer_records | RecordWriterInput.target_records (턴 시작) |
| R6 | 기록 저장소 → Plan 결정 | 저장소 읽기 | 응답·진행·Plan 기록 | SessionStore.answer_records, SessionStore.progress_record, SessionStore.planner_record | DialoguePlannerInput.answer_records (저장 결정 반영 뒤), DialoguePlannerInput.last_directive (턴 시작), DialoguePlannerInput.skipped (턴 시작), DialoguePlannerInput.confirm_stopped (턴 시작), DialoguePlannerInput.open_requests (턴 시작), DialoguePlannerInput.planner_record (턴 시작) |
| R7 | 기록 저장소 → 결과 전달 | 저장소 읽기 | 확정된 최종 기록 | SessionStore.session_info, SessionStore.answer_records, SessionStore.progress_record | DispatchInput.session_info (턴 쓰기 반영 뒤), DispatchInput.answer_records (턴 쓰기 반영 뒤), DispatchInput.skipped (턴 쓰기 반영 뒤), DispatchInput.confirm_stopped (턴 쓰기 반영 뒤), DispatchInput.session_status (턴 쓰기 반영 뒤), DispatchInput.pause_history (턴 쓰기 반영 뒤) |

### 3.2 저장소를 읽는 시점 4가지

| 시점 | 뜻 | 왜 |
|---|---|---|
| 턴 맨 앞 | 세션 정보 생성 전. 세션이 이미 있는지 찾는 데에만 쓴다. | 세션을 만들지 정해야 한다. |
| 턴 시작 | 지난 턴까지 쓰인 값. 새 세션이면 초기값. | 이번 턴 쓰기 전의 상태로 발화를 해석해야 한다. |
| 저장 결정 반영 뒤 | 이번 턴 저장 결정까지 반영된 값. LoRA-A~저장 판단이 돌지 않는 턴에는 턴 시작 값과 같다. | Plan은 방금 저장한 답까지 보고 다음에 물을 것을 정해야 한다. |
| 턴 쓰기 반영 뒤 | 이번 턴의 모든 쓰기가 반영된 값. | 결과 전달은 최종 상태를 넘겨야 한다. |

### 3.3 한 턴을 실행하는 전제 조건 (LangGraph·서빙)

- 같은 세션의 턴은 한 번에 하나씩 처리한다. 앞 턴이 끝나기 전의 입력은 기다린다.
- 한 턴의 쓰기(저장 결정·진행 기록 갱신·Plan 기록 갱신)는 함께 확정된다. 중간에 실패하면 모두 반영되지 않는다. 세션 정보 생성은 턴 맨 앞에서 따로, 전달 기록은 확정 뒤, 대화 로그는 턴 맨 끝에 따로 쓴다(실패한 턴도 남긴다).
- 쓰기 확정 뒤의 일(직원 알림 전달·응답 생성·프론트 전달·결과 전달)은 서로의 성패와 상관없이 한다. 직원 알림 전달이 실패해도 응답은 나가고 턴 실패 신호(직원 알림: 전달 실패)를 보낸다. 쓰기 확정 자체가 실패하면 확정 뒤의 일은 하나도 하지 않는다.
- 한 턴 안에서 저장 판단 이후에 그보다 앞의 컴포넌트로 돌아가지 않는다.

## 4. 경계별 계약 (22개)

필드표의 `필수/선택`은 JSON Schema의 `required`를 뜻한다(값이 없을 수 있는 필드도 키는 반드시 둔다 — null). `↳`는 중첩 필드. 타입 이름이 `SlotRef`처럼 이름만 있으면 §6 공유 타입 사전에 필드가 있다.

### 4.1 프론트 · Frontend  
*외부 접점* — 사용자 말을 STT로 글자로 바꿔 보내고, 응답 문장을 TTS로 읽어 준다.  
왜 따로 두나: 사용자와 닿는 유일한 곳. 시스템 밖이며 받는 값·내는 값만 정한다.

- STT 결과를 `FrontendMessage`로 보낸다. 종류는 세션 시작 신호 / 발화 / 세션 종료 신호 셋뿐이다. 빈 발화도 허용한다(알아듣지 못함으로 처리).
- 응답 문장은 TTS로 읽는다. 턴이 실패하면 `response_text`는 null이고 `turn_failure_signal`이 온다.

#### 프론트 입력 — `FrontendInput` (프론트가 받는 값)
응답 문장과 턴 실패 신호.  
JSON Schema: [`schemas/FrontendInput.json`](schemas/FrontendInput.json)

| 필드 |  | 타입 | 뜻 | 원천 (시점) |
|---|---|---|---|---|
| `response_text` | 필수 | string(≤2000) \| null | **응답 문장** — LoRA-B의 응답 문장. 실패했으면 없음. | LoRA-B·GeneratorOutput.response_text |
| `turn_failure_signal` | 필수 | TurnFailureSignal \| null | **턴 실패 신호** — 실패했을 때. | LangGraph·OrchestratorOutput.turn_failure_signal |

#### 프론트 출력 — `FrontendMessage` (프론트 입력)
프론트가 LangGraph로 보내는 것 하나.  
JSON Schema: [`schemas/FrontendMessage.json`](schemas/FrontendMessage.json)

이 계약은 아래 갈래 중 하나다.

| 갈래 | 뜻 | 필드 (*필수) |
|---|---|---|
| 세션 시작 신호 | 첫 접속·재접속. | session_id*: SessionId, kind*: `SESSION_START` |
| 발화 | 사용자 말(STT 결과). 빈 문자열 가능. | session_id*: SessionId, kind*: `UTTERANCE`, utterance*: string(≤2000) |
| 세션 종료 신호 | 프론트가 세션을 끝냄(떠남). | session_id*: SessionId, kind*: `SESSION_END` |

### 4.2 사람 개입 · Staff Console  
*외부 접점* — 직원·의료진에게 알림을 보여 주고, 그들의 결정(재개·종료)을 보낸다.  
왜 따로 두나: 위험(G1)·직원 요청(F1)에 사람이 와야 하고, 멈춘 문진은 사람만 이어 가거나 끝낼 수 있다.

- 직원·의료진은 재개/종료 두 결정만 보낼 수 있다. 직원 알림·턴 실패 신호·개입 결정 결과를 받아 표시한다.
- 일시 중지(위험) 상태에서는 직원 결정만 처리된다(G5).

#### 사람 개입 입력 — `StaffConsoleInput` (사람 개입이 받는 값)
직원 알림(세션 식별 포함), 턴 실패 신호, 개입 결정 결과.  
JSON Schema: [`schemas/StaffConsoleInput.json`](schemas/StaffConsoleInput.json)

| 필드 |  | 타입 | 뜻 | 원천 (시점) |
|---|---|---|---|---|
| `staff_alert` | 필수 | object \| null | **직원 알림** — 세션 식별과 함께. 없으면 없음. | Plan 결정·PlannerOutput.staff_alert / 기록 저장소·SessionStore.session_info.session_id |
| `turn_failure_signal` | 필수 | TurnFailureSignal \| null | **턴 실패 신호** — 어느 세션이든 턴이 실패하면. | LangGraph·OrchestratorOutput.turn_failure_signal |
| `intervention_result` | 필수 | InterventionResult \| null | **개입 결정 결과** — 보낸 결정의 결과. | LangGraph·OrchestratorOutput.intervention_result |

#### 사람 개입 출력 — `InterventionDecision` (개입 결정)
직원·의료진의 재개·종료.  
JSON Schema: [`schemas/InterventionDecision.json`](schemas/InterventionDecision.json)

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `session_id` | 필수 | SessionId | **세션 식별** — 어느 세션의 값인지. |
| `decision` | 필수 | Decision | **결정** — 재개 또는 종료. |

### 4.3 LangGraph · Orchestrator  
*흐름 제어* — 한 턴의 순서대로 컴포넌트를 부르고, 저장소에서 정해진 범위를 가져와 건네고, 쓰기를 저장소에 전달한다.  
왜 따로 두나: 컴포넌트가 저장소를 직접 읽으면 무엇에 의존하는지가 코드 안에 숨고 혼자 시험할 수 없다. 읽기·쓰기 순서를 한 곳에서 지켜야 한 턴 안에서 어긋나지 않는다.

- 턴 시작 입력(프론트 입력 또는 개입 결정, 둘 중 정확히 하나)과 세션 상태로 **처리 표(9-1절)** 의 행을 고른다.
- 처리 표·흐름 종료(결과 전달 호출)·턴 실패 말고는 **분기하지 않는다**. 판정 상태나 행동 종류로 분기하지 않는다(행동을 바꿀 때 Plan과 LoRA-B만 바뀌게).
- 세션은 만들어진 시점의 문항 정의 버전을 계속 쓴다(J1). 각 경계 값은 계약으로 검증한 뒤 다음 컴포넌트로 넘긴다.
- 저장소에서 정해진 범위만 가져온다(판단 없는 고르기). 대화 로그는 턴 끝에 따로 쓰며 실패한 턴도 남긴다.

#### LangGraph 입력 — `OrchestratorInput` (LangGraph가 받는 값)
턴 시작 입력과 세션 상태.  
JSON Schema: [`schemas/OrchestratorInput.json`](schemas/OrchestratorInput.json)

| 필드 |  | 타입 | 뜻 | 원천 (시점) |
|---|---|---|---|---|
| `frontend_input` | 필수 | FrontendMessage \| null | **프론트 입력** — 이번 턴 입력이 프론트에서 왔으면. | 프론트·FrontendMessage |
| `intervention_decision` | 필수 | InterventionDecision \| null | **개입 결정** — 이번 턴 입력이 사람 개입에서 왔으면. | 사람 개입·InterventionDecision |
| `session_found` | 필수 | boolean | **세션 있음** — 기록 저장소 · 받은 세션 식별과 같은 세션 정보가 있는지(턴 맨 앞). | 기록 저장소·SessionStore.session_info.session_id (턴 맨 앞) |
| `session_question_bank_version` | 필수 | integer(0..1000) \| null | **이 세션의 문항 정의 버전** — 기록 저장소 · 세션 정보.문항 정의 버전(턴 시작). 세션이 없으면 없음. | 기록 저장소·SessionStore.session_info.question_bank_version (턴 시작) |
| `session_status` | 필수 | SessionStatus \| null | **세션 상태** — 기록 저장소 · 진행 기록.세션 상태(턴 시작). 세션이 없으면 없음. | 기록 저장소·SessionStore.progress_record.session_status (턴 시작) |
| `latest_question_bank_version` | 필수 | integer(0..1000) | **최신 문항 정의 버전** — 문항 정의 저장소 · 가장 큰 버전. | 문항 정의 저장소·QuestionBank.version |

#### LangGraph 출력 — `OrchestratorOutput` (LangGraph가 내는 값)
턴 종류, 세션 정보 생성, 대화 로그 항목, 턴 실패 신호, 개입 결정 결과, 결과 전달 호출 여부.  
JSON Schema: [`schemas/OrchestratorOutput.json`](schemas/OrchestratorOutput.json)

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `turn_kind` | 필수 | TurnKind \| null | **턴 종류** — 처리 표로 정한 턴 종류. 처리 안 함이면 없음. |
| `session_info_created` | 필수 | SessionInfo \| null | **세션 정보 생성** — 세션이 없을 때 한 번. 아니면 없음. |
| `log_entry` | 필수 | LogEntry \| null | **대화 로그 항목** — 남기지 않는 경우(세션 없음 열의 처리 안 함, 세션 정보 생성에 실패한 턴, 종료 열의 처리 안 함)는 없음. |
| `turn_failure_signal` | 필수 | TurnFailureSignal \| null | **턴 실패 신호** — 실패했을 때. |
| `intervention_result` | 필수 | InterventionResult \| null | **개입 결정 결과** — 개입 결정이 들어온 턴마다. |
| `dispatch_called` | 필수 | boolean | **결과 전달 호출** — 흐름이 종료라 결과 전달을 불렀는지. |

### 4.4 LoRA-A · Utterance Parser  
*모델* — 사용자 발화를 (대상, 값, 원문, 의도) 항목들로 바꾼다.  
왜 따로 두나: 자연어 해석만 모델이 하고 판단은 코드가 한다(업무분담 원칙).

- 발화를 (대상, 값, 원문, 의도) 항목으로 바꾸는 일만 한다. 값은 **표준화하지 않는다**(원문 문자열).
- 저장 여부·다음 질문·최종 문장·상태 판정은 하지 않는다.
- 대체 출력(J7): 형식을 못 지키면 빈 목록, 어휘 밖 의도는 인식불가, 대상을 못 정한 답함은 인식불가 등. 정의에 없는 대상은 그대로 내고 정규화·검증이 표시한다.

#### LoRA-A 입력 — `UtteranceParserInput` (LoRA-A가 받는 값)
업무분담 LoRA-A Input(session_id·question_id·question_schema·user_utterance·relevant_state)에 대응. 현재 1턴을 기본으로 하고 필요한 상태만 더한다는 업무분담 원칙을 따른다.  
JSON Schema: [`schemas/UtteranceParserInput.json`](schemas/UtteranceParserInput.json)

| 필드 |  | 타입 | 뜻 | 원천 (시점) |
|---|---|---|---|---|
| `utterance` | 필수 | string(≤2000) | **발화** — 프론트 · 발화. | 프론트·FrontendMessage |
| `last_directive` | 필수 | Directive \| null | **직전 응답 지시** — 기록 저장소 · 진행 기록.직전 응답 지시(턴 시작). | 기록 저장소·SessionStore.progress_record.last_directive (턴 시작) |
| `awaiting_questions` | 필수 | array<QuestionDef> | **기다리는 답의 대상 문항 정의** — 문항 정의 저장소 · 직전 응답 지시의 기다리는 답 대상 문항과 그 슬롯 전부. 없으면 빈 목록. | 문항 정의 저장소·QuestionBank.questions |
| `question_names` | 필수 | array<object> | **전체 문항 이름 목록** — 문항 정의 저장소 · 모든 문항의 ID·이름과 슬롯 ID. | 문항 정의 저장소·QuestionBank.questions |
| `↳ question_names[].question_id` | 필수 | QuestionId | **문항 ID** — 문항. |  |
| `↳ question_names[].name` | 필수 | string(≤2000) | **이름** — 문항 이름. |  |
| `↳ question_names[].slots` | 필수 | array<string> | **슬롯** — 슬롯 ID들. 슬롯 ID가 곧 말로 부르는 이름이다(개비, 수축기). |  |
| `answered_slots` | 필수 | array<object> | **답한 슬롯 목록** — 기록 저장소 · 응답 기록에서 현재값이 답인 슬롯의 값(턴 시작). 모름·거절은 넣지 않는다. | 기록 저장소·SessionStore.answer_records (턴 시작) |
| `↳ answered_slots[].slot` | 필수 | SlotRef | **슬롯** — 현재 확정된 답을 함께 제공하는 문항·반복 행·슬롯의 식별자. |  |
| `↳ answered_slots[].value` | 필수 | Value | **값** — 현재값. |  |
| `guide_list` | 필수 | array<object> | **안내 목록** — 문항 정의 저장소 · 세션 설정.안내 목록의 ID와 고르는 기준. 문장은 넣지 않는다(고르기만 한다). | 문항 정의 저장소·QuestionBank.session_settings.guide_list |
| `↳ guide_list[].guide_id` | 필수 | string | **안내 항목 ID** — 안내 선택 기준에 대응하는 등록 안내 항목의 ID. 모델이 guide_id로 선택할 수 있는 값이다. |  |
| `↳ guide_list[].selection_criterion` | 필수 | string(≤2000) | **고르는 기준** — 설명. |  |

#### LoRA-A 출력 — `ParserOutput` (LoRA-A 출력)
항목 목록. 빈 발화면 빈 목록.  
JSON Schema: [`schemas/ParserOutput.json`](schemas/ParserOutput.json)

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `items` | 필수 | array<Item> | **항목 목록** — 발화에서 뽑은 항목들. |

### 4.5 정규화·검증 · Answer Normalizer  
*코드* — 항목 값을 표준 형태로 바꾸고, 규칙 위반·기존 값과의 같음/다름·빠진 필수 슬롯·선행 조건을 사실로 표시한다.  
왜 따로 두나: 값 규칙(단위·범위·선행 조건)이 바뀌면 이곳만 바뀐다.

- 값 표준화(단위 환산 포함)와 내용 검사를 한다. 문제가 있는 항목도 되돌려 보내지 않고 **문제로 표시해 넘긴다**.
- 기존 값·확인 대기 값과의 같음/다름, 빠진 필수 슬롯, 선행 조건(엄격 원칙)을 사실로 표시한다.
- 값 비교·위험 기준 판단은 이 컴포넌트에서만 한다.

#### 정규화·검증 입력 — `AnswerNormalizerInput` (정규화·검증이 받는 값)
항목 목록과 관련 문항의 규칙·현재값·확인 대기·기다리는 답.  
JSON Schema: [`schemas/AnswerNormalizerInput.json`](schemas/AnswerNormalizerInput.json)

| 필드 |  | 타입 | 뜻 | 원천 (시점) |
|---|---|---|---|---|
| `items` | 필수 | array<Item> | **항목 목록** — LoRA-A · 항목 목록. | LoRA-A·ParserOutput.items |
| `related_questions` | 필수 | array<QuestionDef> | **관련 문항 정의** — 문항 정의 저장소 · 항목이 가리킨 문항, 기다리는 답의 대상 슬롯이 속한 문항, 그리고 그것들의 선행 조건이 가리키는 문항의 정의. 정의에 없는 문항은 넣지 않는다(정의에 없는 대상 검사에 쓰인다). | 문항 정의 저장소·QuestionBank.questions |
| `current_values` | 필수 | array<object> | **현재값** — 기록 저장소 · 관련 슬롯의 현재값(턴 시작). | 기록 저장소·SessionStore.answer_records (턴 시작) |
| `↳ current_values[].slot` | 필수 | SlotRef | **슬롯** — 이 current_value와 비교할 이번 턴의 대상 슬롯 식별자. |  |
| `↳ current_values[].current_value` | 필수 | CurrentValue | **현재값** — 현재값. |  |
| `pendings` | 필수 | array<object> | **확인 대기 값** — 기록 저장소 · 관련 슬롯과 기다리는 답 대상 슬롯 중 확인 대기가 있는 것(턴 시작). | 기록 저장소·SessionStore.answer_records (턴 시작) |
| `↳ pendings[].pending_id` | 필수 | PendingId | **확인 대기 ID** — 값 비교·확인 수락의 대상으로 사용되는 현재 확인 대기의 ID. |  |
| `↳ pendings[].slot` | 필수 | SlotRef | **슬롯** — 이 확인 대기 값이 속한 문항·반복 행·슬롯의 식별자. |  |
| `↳ pendings[].value` | 필수 | Value | **값** — 확인 대기 값. |  |
| `awaiting` | 필수 | object \| null | **기다리는 답** — 기록 저장소 · 직전 응답 지시의 기다리는 답 중 행동·대상 목록·대상 확인 대기 ID(턴 시작). | 기록 저장소·SessionStore.progress_record.last_directive (턴 시작) |

#### 정규화·검증 출력 — `NormalizerOutput` (정규화·검증 출력)
항목별 검사와 빠진 필수 슬롯.  
JSON Schema: [`schemas/NormalizerOutput.json`](schemas/NormalizerOutput.json)

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `item_checks` | 필수 | array<ItemCheck> | **항목별 검사** — 항목마다 하나. |
| `missing_required_slots` | 필수 | array<SlotRef> | **빠진 필수 슬롯** — 이번에 답한 문항에서 이번 값도, 모름·거절도 없고 현재값도 없음인 필수 슬롯. 선행 답이 정해지지 않았거나 선행 조건과 맞지 않는 문항(선행 불충족·다른 답과 맞지 않음인 항목의 문항)은 따지지 않는다. |

### 4.6 상태 판정 · Answer Judge  
*코드* — 이번 발화가 각 대상에 대해 무엇을 뜻하는지(정상·정정·충돌·누락 등) 판정한다.  
왜 따로 두나: 해석 규칙(충돌·정정·확인 응답)이 바뀌면 이곳만 바뀐다. 저장 판단보다 먼저 있어야 한다(업무분담과 다른 점).

- 항목 하나씩 “기다리는 답” 표로 처리한 뒤 대상별로 합쳐 판정한다. 상태는 위에서부터 처음 맞는 것(선행 불충족 → 모름·거절 → 애매 → 정정 → 정상 → 충돌).
- 확인 대기가 있는 슬롯은 받아들임·버림·새로 둠을 함께 낸다. 위험 신호는 무엇을 기다리든 먼저다.
- 정정·모름·거절·받아들임이면 영향받는 후속 문항을 무효화 대상으로 낸다.

#### 상태 판정 입력 — `AnswerJudgeInput` (상태 판정이 받는 값)
항목·검사·발화 원문·위험 표현·직전 응답 지시·확인 대기 목록·후속 문항·슬롯 목록.  
JSON Schema: [`schemas/AnswerJudgeInput.json`](schemas/AnswerJudgeInput.json)

| 필드 |  | 타입 | 뜻 | 원천 (시점) |
|---|---|---|---|---|
| `items` | 필수 | array<Item> | **항목 목록** — LoRA-A · 항목 목록. | LoRA-A·ParserOutput.items |
| `item_checks` | 필수 | array<ItemCheck> | **항목별 검사** — 정규화·검증 · 항목별 검사. | 정규화·검증·NormalizerOutput.item_checks |
| `missing_required_slots` | 필수 | array<SlotRef> | **빠진 필수 슬롯** — 정규화·검증 · 빠진 필수 슬롯. | 정규화·검증·NormalizerOutput.missing_required_slots |
| `utterance` | 필수 | string(≤2000) | **발화 원문** — 프론트 · 발화. | 프론트·FrontendMessage |
| `risk_phrases` | 필수 | array<string(≤2000)> | **위험 표현 목록** — 문항 정의 저장소 · 세션 설정.위험 표현 목록. | 문항 정의 저장소·QuestionBank.session_settings.risk_phrases |
| `last_directive` | 필수 | Directive \| null | **직전 응답 지시** — 기록 저장소 · 진행 기록.직전 응답 지시(턴 시작). | 기록 저장소·SessionStore.progress_record.last_directive (턴 시작) |
| `pendings` | 필수 | array<object> | **확인 대기 목록** — 기록 저장소 · 확인 대기가 있는 모든 슬롯(턴 시작). | 기록 저장소·SessionStore.answer_records (턴 시작) |
| `↳ pendings[].pending_id` | 필수 | PendingId | **확인 대기 ID** — 이번 확인 응답이 수락·폐기할 현재 확인 대기의 ID. |  |
| `↳ pendings[].slot` | 필수 | SlotRef | **슬롯** — 이 확인 대기를 수락·폐기했을 때 바뀔 문항·반복 행·슬롯의 식별자. |  |
| `affected_followups` | 필수 | array<object> | **영향받는 후속 문항** — 문항 정의 저장소 · 모든 문항의 영향받는 후속 문항. | 문항 정의 저장소·QuestionBank.questions |
| `↳ affected_followups[].question_id` | 필수 | QuestionId | **문항 ID** — 문항. |  |
| `↳ affected_followups[].followups` | 필수 | array<QuestionId> | **후속 문항** — 영향받는 후속 문항. |  |
| `question_slots` | 필수 | array<object> | **문항의 슬롯 목록** — 문항 정의 저장소 · 항목에 문항 전체로 나온 문항의 슬롯 ID 전부. | 문항 정의 저장소·QuestionBank.questions |
| `↳ question_slots[].question_id` | 필수 | QuestionId | **문항 ID** — 문항. |  |
| `↳ question_slots[].slot_ids` | 필수 | array<string> | **슬롯 ID** — 슬롯들. |  |

#### 상태 판정 출력 — `JudgeOutput` (상태 판정 출력)
판정, 무효화 대상 문항, 발화 판정.  
JSON Schema: [`schemas/JudgeOutput.json`](schemas/JudgeOutput.json)

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `judgments` | 필수 | array<Judgment> | **판정** — 대상마다. |
| `invalidated_questions` | 필수 | array<QuestionId> | **무효화 대상 문항** — 판정이 정정·모름·거절·받아들임인 슬롯의 문항의 영향받는 후속 문항 전부(첫 답인지 따지지 않는다). |
| `utterance_judgment` | 필수 | UtteranceJudgment | **발화 판정** — 발화 전체에 대한 판정. |

### 4.7 저장 판단 · Record Writer  
*코드* — 판정을 응답 기록에 어떻게 반영할지 슬롯별로 정한다.  
왜 따로 두나: 저장소가 판단 없이 반영하게 하려면 무엇을 할지가 다 정해져 있어야 한다.

- 판정을 슬롯별 저장 결정으로 펼친다. 변경 없는 슬롯은 내지 않고, 무효화를 먼저 낸다.
- 애매·누락·선행 불충족은 저장하지 않는다. 확인 대기 ID는 확인 대기 둠마다 새로 만든다.

#### 저장 판단 입력 — `RecordWriterInput` (저장 판단이 받는 값)
판정·무효화 대상 문항·슬롯 목록·기록 대상 슬롯의 응답 기록.  
JSON Schema: [`schemas/RecordWriterInput.json`](schemas/RecordWriterInput.json)

| 필드 |  | 타입 | 뜻 | 원천 (시점) |
|---|---|---|---|---|
| `judgments` | 필수 | array<Judgment> | **판정** — 상태 판정 · 판정. | 상태 판정·JudgeOutput.judgments |
| `invalidated_questions` | 필수 | array<QuestionId> | **무효화 대상 문항** — 상태 판정 · 무효화 대상 문항. | 상태 판정·JudgeOutput.invalidated_questions |
| `question_slots` | 필수 | array<object> | **문항의 슬롯 목록** — 문항 정의 저장소 · 문항 전체 판정의 문항과 무효화 대상 문항의 슬롯 전부. | 문항 정의 저장소·QuestionBank.questions |
| `↳ question_slots[].question_id` | 필수 | QuestionId | **문항 ID** — 문항. |  |
| `↳ question_slots[].slot_ids` | 필수 | array<string> | **슬롯 ID** — 슬롯들. |  |
| `target_records` | 필수 | array<object> | **기록 대상 슬롯의 응답 기록** — 기록 저장소 · 기록 대상 슬롯마다 현재값과 확인 대기(턴 시작). 기록이 없으면 현재값 없음, 확인 대기 없음. | 기록 저장소·SessionStore.answer_records (턴 시작) |
| `↳ target_records[].slot` | 필수 | SlotRef | **슬롯** — 저장 판단이 current_value·pending을 읽고 쓰기 결정을 적용할 대상 슬롯 식별자. |  |
| `↳ target_records[].current_value` | 필수 | CurrentValue | **현재값** — 현재값. |  |
| `↳ target_records[].pending` | 필수 | PendingRecord \| null | **확인 대기** — 확인 대기. |  |

#### 저장 판단 출력 — `StoreResult` (저장 판단 출력)
저장 결정과 저장 결과 요약.  
JSON Schema: [`schemas/StoreResult.json`](schemas/StoreResult.json)

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `store_decisions` | 필수 | array<StoreDecision> | **저장 결정** — 슬롯별 쓰기. |
| `store_summary` | 필수 | StoreSummary | **저장 결과 요약** — 바뀐 것. |

### 4.8 Plan 결정 · Dialogue Planner  
*코드* — 다음에 무엇을 말할지 정하고, 그 말에 필요한 값과 문장 재료를 담은 응답 지시를 만든다.  
왜 따로 두나: 대화 정책이 바뀌면 이곳만 바뀐다. 진행 기록·Plan 기록을 쓰는 유일한 곳.

- 다음에 무엇을 말할지 정한다. **저장하지 않고 매 턴 사실에서 다시 계산**한다. 진행 기록·Plan 기록을 쓰는 유일한 곳.
- 발화 턴은 8-1절의 순서(위험 → 사람 요청 → 중단 → … → 종료 확인)로 처음 맞는 규칙을 따른다. 한 턴에 행동은 하나다.
- 상한(질문·확인·물음)에 닿으면 건너뜀·확인 중단·열린 요청 제거·도움 요청으로 반복을 끝낸다.

#### Plan 결정 입력 — `DialoguePlannerInput` (Plan이 받는 값)
턴 종류, 이번 턴 판정들, 저장 뒤 응답 기록, 진행 기록의 사실, Plan 기록, 문항 정의 전체.  
JSON Schema: [`schemas/DialoguePlannerInput.json`](schemas/DialoguePlannerInput.json)

| 필드 |  | 타입 | 뜻 | 원천 (시점) |
|---|---|---|---|---|
| `turn_kind` | 필수 | TurnKind | **턴 종류** — LangGraph · 턴 종류. | LangGraph·OrchestratorOutput.turn_kind |
| `utterance_judgment` | 필수 | UtteranceJudgment \| null | **발화 판정** — 상태 판정 · 발화 판정. 발화 턴에만. | 상태 판정·JudgeOutput.utterance_judgment |
| `judgments` | 필수 | array<Judgment> | **판정** — 상태 판정 · 판정. 발화 턴이 아니면 빈 목록. | 상태 판정·JudgeOutput.judgments |
| `store_summary` | 필수 | StoreSummary \| null | **저장 결과 요약** — 저장 판단 · 저장 결과 요약. 발화 턴에만. | 저장 판단·StoreResult.store_summary |
| `answer_records` | 필수 | array<SlotRecord> | **응답 기록** — 기록 저장소 · 모든 슬롯(저장 결정 반영 뒤). | 기록 저장소·SessionStore.answer_records (저장 결정 반영 뒤) |
| `last_directive` | 필수 | Directive \| null | **직전 응답 지시** — 기록 저장소 · 진행 기록.직전 응답 지시(턴 시작). | 기록 저장소·SessionStore.progress_record.last_directive (턴 시작) |
| `skipped` | 필수 | array<SkipEntry> | **건너뜀** — 기록 저장소 · 진행 기록.건너뜀(턴 시작). | 기록 저장소·SessionStore.progress_record.skipped (턴 시작) |
| `confirm_stopped` | 필수 | array<SlotRef> | **확인 중단** — 기록 저장소 · 진행 기록.확인 중단(턴 시작). | 기록 저장소·SessionStore.progress_record.confirm_stopped (턴 시작) |
| `open_requests` | 필수 | OpenRequests | **열린 요청** — 기록 저장소 · 진행 기록.열린 요청(턴 시작). | 기록 저장소·SessionStore.progress_record.open_requests (턴 시작) |
| `planner_record` | 필수 | PlannerRecord | **Plan 기록** — 기록 저장소 · Plan 기록(턴 시작). | 기록 저장소·SessionStore.planner_record (턴 시작) |
| `question_bank` | 필수 | QuestionBank | **문항 정의** — 문항 정의 저장소 · 이 세션 버전 전체. | 문항 정의 저장소·QuestionBank |

#### Plan 결정 출력 — `PlannerOutput` (Plan 출력)
응답 지시, 흐름, 직원 알림, 진행 기록 갱신, Plan 기록 갱신.  
JSON Schema: [`schemas/PlannerOutput.json`](schemas/PlannerOutput.json)

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `directive` | 필수 | Directive | **응답 지시** — LoRA-B로. |
| `flow` | 필수 | Flow | **흐름** — 이번 턴 뒤 세션을 닫을지. |
| `staff_alert` | 필수 | StaffAlert \| null | **직원 알림** — 위험·도움 요청·사람 요청일 때. 아니면 없음. |
| `progress_record_update` | 필수 | ProgressRecordUpdate | **진행 기록 갱신** — 기록 저장소로. |
| `planner_record_update` | 필수 | PlannerRecord | **Plan 기록 갱신** — Plan 기록 전체의 새 값. |

### 4.9 LoRA-B · Response Generator  
*모델* — 응답 지시를 사용자 발화에 맞춰 받아 주며 자연스러운 문장으로 바꾼다.  
왜 따로 두나: 문장만 모델이 만들고 무엇을 말할지는 정하지 않는다(업무분담 원칙).

- 응답 지시를 자연스러운 문장으로 바꾸기만 한다. 응답 지시에 없는 값·문항을 말하지 않는다.
- 위험 안내는 받아 주는 말 없이 문장 재료대로만 말한다. 지시 밖 물음에는 도와드리기 어렵다고만 한다.
- 대체 출력(J7): 규칙을 지키지 못하면 문장 재료를 그대로 읽는 문장을 내고 `is_fallback=true`.

#### LoRA-B 입력 — `ResponseGeneratorInput` (LoRA-B가 받는 값)
응답 지시와 발화.  
JSON Schema: [`schemas/ResponseGeneratorInput.json`](schemas/ResponseGeneratorInput.json)

| 필드 |  | 타입 | 뜻 | 원천 (시점) |
|---|---|---|---|---|
| `directive` | 필수 | Directive | **응답 지시** — Plan 결정 · 응답 지시. | Plan 결정·PlannerOutput.directive |
| `utterance` | 필수 | string(≤2000) \| null | **발화** — 프론트 · 발화. 발화 턴에만. | 프론트·FrontendMessage |

#### LoRA-B 출력 — `GeneratorOutput` (LoRA-B 출력)
응답 문장.  
JSON Schema: [`schemas/GeneratorOutput.json`](schemas/GeneratorOutput.json)

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `response_text` | 필수 | string(≤2000) | **응답 문장** — 사용자에게 할 말. |
| `is_fallback` | 필수 | boolean | **대체 출력** — 출력 계약을 지키지 못해 문장 재료를 그대로 읽는 문장을 냈으면 true. |

### 4.10 결과 전달 · Result Dispatcher  
*외부 접점(붙을 예정)* — 확정된 문진 결과를 시스템 밖으로 넘긴다.  
왜 따로 두나: 업무분담 COMPLETE의 Finalization 기록. 받는 곳이 정해지면 넘기는 형식을 정한다.

- 흐름이 END일 때만 불린다. 확정된 문진 결과(세션 정보·응답 기록·건너뜀·확인 중단·세션 상태·중지 이력)를 받아 밖으로 넘긴다.
- 밖으로 넘기는 결과의 형식은 받는 곳이 정해지면 정한다(이 스키마 밖). 계약이 정하는 것은 전달 기록 한 건뿐이다.

#### 결과 전달 입력 — `DispatchInput` (결과 전달이 받는 값)
세션 정보·응답 기록·건너뜀·확인 중단·세션 상태·중지 이력·문항 정의(턴 쓰기 반영 뒤).  
JSON Schema: [`schemas/DispatchInput.json`](schemas/DispatchInput.json)

| 필드 |  | 타입 | 뜻 | 원천 (시점) |
|---|---|---|---|---|
| `session_info` | 필수 | SessionInfo | **세션 정보** — 기록 저장소 · 세션 정보. | 기록 저장소·SessionStore.session_info (턴 쓰기 반영 뒤) |
| `answer_records` | 필수 | array<SlotRecord> | **응답 기록** — 기록 저장소 · 모든 슬롯. | 기록 저장소·SessionStore.answer_records (턴 쓰기 반영 뒤) |
| `skipped` | 필수 | array<SkipEntry> | **건너뜀** — 기록 저장소 · 진행 기록.건너뜀. | 기록 저장소·SessionStore.progress_record.skipped (턴 쓰기 반영 뒤) |
| `confirm_stopped` | 필수 | array<SlotRef> | **확인 중단** — 기록 저장소 · 진행 기록.확인 중단. | 기록 저장소·SessionStore.progress_record.confirm_stopped (턴 쓰기 반영 뒤) |
| `session_status` | 필수 | SessionStatus | **세션 상태** — 기록 저장소 · 진행 기록.세션 상태. | 기록 저장소·SessionStore.progress_record.session_status (턴 쓰기 반영 뒤) |
| `pause_history` | 필수 | array<PauseEntry> | **중지 이력** — 기록 저장소 · 진행 기록.중지 이력. | 기록 저장소·SessionStore.progress_record.pause_history (턴 쓰기 반영 뒤) |

#### 결과 전달 출력 — `DispatchOutput` (결과 전달이 내는 값)
전달 기록 한 건. 밖으로 넘기는 문진 결과의 형식은 받는 곳이 정해지면 정한다(이 스키마 밖).  
JSON Schema: [`schemas/DispatchOutput.json`](schemas/DispatchOutput.json)

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `dispatch_record` | 필수 | DispatchRecord | **전달 기록** — 한 건. |

### 4.11 문항 정의 저장소 · Question Bank  
*저장소* — 문진 설계자가 등록한 문항 정의를 버전별로 읽기 전용으로 보관한다.  
왜 따로 두나: 문항을 코드 밖에 두어 문항을 바꿔도 코드가 바뀌지 않는다.


#### 문항 정의 저장소 상태 — `QuestionBank` (문항 정의 저장소)
한 버전의 문항 정의 전체. 운영 중 바뀌지 않는다.  
JSON Schema: [`schemas/QuestionBank.json`](schemas/QuestionBank.json)

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `version` | 필수 | integer(0..1000) | **버전** — 버전 번호. |
| `questions` | 필수 | array<QuestionDef> | **문항** — 문항들. |
| `session_settings` | 필수 | SessionSettings | **세션 설정** — 설정. |

### 4.12 기록 저장소 · Session Store  
*저장소* — 세션별 응답 기록·진행 기록·Plan 기록·세션 정보·로그를 보관하고, 받은 쓰기를 정해진 효과대로 반영한다.  
왜 따로 두나: 턴 사이에 이어져야 하는 사실을 둔다.


#### 기록 저장소 상태 — `SessionStore` (기록 저장소)
세션 하나의 기록 전체.  
JSON Schema: [`schemas/SessionStore.json`](schemas/SessionStore.json)

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `session_info` | 필수 | SessionInfo | **세션 정보** — LangGraph가 세션을 만들 때 한 번 쓴다. |
| `answer_records` | 필수 | array<SlotRecord> | **응답 기록** — 슬롯별 기록. 저장 판단만 쓴다. |
| `progress_record` | 필수 | ProgressRecord | **진행 기록** — Plan만 쓴다. |
| `planner_record` | 필수 | PlannerRecord | **Plan 기록** — Plan만 쓰고 읽는다. |
| `dialogue_log` | 필수 | array<LogEntry> | **대화 로그** — LangGraph만 쓴다. 시스템 안에서 읽는 컴포넌트는 없다. |
| `dispatch_log` | 필수 | array<DispatchRecord> | **전달 기록** — 결과 전달만 쓴다. |

## 5. 코드 어휘 (값 목록)

공유 어휘는 컴포넌트 사이에서 같은 글자로 오간다. 새 값을 만들면 Schema와 필드 설명을 함께 고쳐야 한다.

**턴 종류** (`TurnKind`)

| 값 | 이름 | 뜻 |
|---|---|---|
| `SESSION_START` | 세션 시작 | 첫 접속·재접속 |
| `UTTERANCE` | 발화 | 사용자 말 |
| `RESUME` | 재개 | 위험 일시 중지 뒤 직원이 재개 |
| `INTERVENTION_END` | 개입 종료 | 직원이 끝냄 |
| `END_LEFT` | 이탈 종료 | 프론트가 떠났다고 알림 |

**입력 종류** (`InputKind`)

| 값 | 이름 | 뜻 |
|---|---|---|
| `SESSION_START` | 세션 시작 신호 | 첫 접속·재접속 |
| `UTTERANCE` | 발화 | 사용자 말 |
| `INTERVENTION` | 개입 결정 | 직원의 재개·종료 |
| `SESSION_END` | 세션 종료 신호 | 사용자가 떠남 |

**LoRA-A 의도** (`Intent`)

| 값 | 이름 | 뜻 |
|---|---|---|
| `ANSWERED_INTENT` | 답함 | 묻는 문항(또는 다른 문항)에 값을 말함 |
| `CORRECTION_MARKED` | 정정 | 앞서 한 답을 고친다는 표지와 함께 말함 |
| `CONFIRM_YES` | 확인-긍정 | 확인 질문에 "네" |
| `CONFIRM_NO` | 확인-부정 | 확인 질문에 "아니요" |
| `SAYS_UNKNOWN` | 모름 | 모른다고 함 |
| `SAYS_REFUSAL` | 거절 | 답하지 않겠다고 함 |
| `PROGRESS_OP` | 진행 조작 | 반복·대기·나중에·중단 요청 |
| `GUIDE_REQUEST` | 안내 요청 | 안내 목록에 있는 물음(뜻, 남은 수 등) |
| `USER_CALLED_STAFF` | 사람 요청 | 직원을 찾거나 시스템이 할 수 없는 요청 |
| `OUT_OF_SCOPE` | 무관 | 문진·안내 목록과 상관없는 말 |
| `UNRECOGNIZED` | 인식불가 | 무슨 말인지 알 수 없음 |
| `RISK_SIGNAL` | 위험 신호 | 지금 위급하다는 말 |

**판정 상태** (`JudgmentStatus`)

| 값 | 이름 | 뜻 |
|---|---|---|
| `ANSWERED` | 정상 | 쓸 수 있는 값(첫 답이거나 기존과 같음) |
| `MISSING` | 누락 | 같은 문항의 필수 슬롯이 빠짐 |
| `UNCLEAR` | 애매 | 값에 문제가 있음 |
| `CONFLICT` | 충돌 | 표지 없이 기존 답과 다른 값 |
| `CORRECTION` | 정정 | 고친 값이 확정됨 |
| `UNKNOWN` | 모름 | 모름 |
| `REJECTED` | 거절 | 거절 |
| `PREREQUISITE_UNMET` | 선행 불충족 | 선행 조건이 정해지지 않았거나 맞지 않는 후속 문항에 대한 말 |

**발화 판정 결과** (`UtteranceResult`)

| 값 | 이름 | 뜻 |
|---|---|---|
| `HAS_ANSWER` | 응답 있음 | 판정·확인 응답·값 없는 정정 요청·위험 신호 중 하나라도 있음 |
| `REQUEST_ONLY` | 요청만 | 위의 것은 없고 요청이 있음 |
| `OUT_OF_SCOPE_ONLY` | 무관만 | 위의 것도 요청도 없고 무관 항목이 있음 |
| `UNRECOGNIZED_TURN` | 알아듣지 못함 | 그 밖(빈 발화, 인식불가뿐) |

**저장 동작** (`StoreAction`)

| 값 | 이름 | 뜻 |
|---|---|---|
| `FIRST_WRITE` | 첫 저장 | 빈 슬롯에 값을 넣음 |
| `NEW_REVISION` | 새 revision | 있던 답을 고침(이전 답은 이력으로) |
| `RECORD_UNKNOWN` | 모름 기록 | 모름으로 기록 |
| `RECORD_REFUSAL` | 거절 기록 | 거절로 기록 |
| `SET_PENDING` | 확인 대기 둠 | 기존 값은 두고 새 값을 확인 대기에 둠 |
| `ACCEPT_PENDING` | 확인 대기 받아들임 | 확인 대기 값을 현재값으로 |
| `DROP_PENDING` | 확인 대기 버림 | 확인 대기를 지움 |
| `INVALIDATE` | 무효화 | 선행 답이 바뀌어 후속 답을 지움 |

**Plan 행동** (`Action`)

| 값 | 이름 | 뜻 |
|---|---|---|
| `ASK_NEXT` | 다음 문항 묻기 | 열린 문항을 묻는다 |
| `ASK_MISSING` | 빠진 슬롯 되묻기 | 같은 문항의 빠진 필수 슬롯만 묻는다 |
| `ASK_CLARIFY` | 구체화 요청 | 애매한 값을 짚어 다시 묻는다 |
| `ASK_CONFIRM` | 확인 대기 확인 | 기존 답과 새 답 중 어느 것이 맞는지 묻는다 |
| `ASK_AFTER_UNKNOWN` | 모름 뒤 재질문 | 모름에 한 번 더 묻는다 |
| `ASK_AFTER_REFUSAL` | 거절 시 설명 후 재질문 | 왜 묻는지 설명하고 다시 묻는다 |
| `ASK_CORRECTION_TARGET` | 정정 구체화 | 무엇을, 어떤 값으로 고칠지 묻는다 |
| `ASK_FINISH` | 종료 확인 | 마칠지 묻는다 |
| `ASK_STOP` | 중단 확인 | 정말 그만둘지 묻는다 |
| `ASK_REPEAT` | 다시 말씀 요청 | 알아듣지 못했으니 다시 말해 달라 |
| `CALL_STAFF` | 도움 요청 | 알아듣지 못함이 이어져 직원을 부른다 |
| `REDIRECT` | 무관 안내 후 다시 묻기 | 받아 주고 하던 질문을 잇는다 |
| `RISK_NOTICE` | 위험 안내 | 위급 안내를 하고 멈춘다 |
| `WAIT_NOTICE` | 대기 안내 | 기다리겠다고 한다 |
| `STAFF_NOTICE` | 사람 연결 안내 | 직원을 불렀다고 한다 |
| `FAREWELL` | 종료 인사 | 마친다 |

**알릴 것 종류** (`NoticeKind`)

| 값 | 이름 | 뜻 |
|---|---|---|
| `CORRECTION_ACK` | 정정 받았음 | 값을 고쳤다 |
| `KEPT_PREVIOUS` | 기존 답 유지 | 기존 답을 그대로 둔다 |
| `RESUME` | 재개 | 다시 이어 간다 |
| `SURVEY_STOPPED` | 문진 중단 | 여기서 그만둔다 |
| `GUIDE` | 안내 | 안내 문장 |
| `DEFERRED` | 미룸 | 이 문항은 나중에 묻는다 |

**요청 종류** (`RequestKind`)

| 값 | 이름 | 뜻 |
|---|---|---|
| `REPEAT` | 반복 | 다시 말해 달라 |
| `WAIT` | 대기 | 기다려 달라 |
| `LATER` | 나중에 | 이 문항은 나중에 |
| `STOP` | 중단 | 그만하겠다 |
| `GUIDE` | 안내 | 안내 목록의 물음 |
| `STAFF_REQUEST` | 사람 | 직원 요청 |

**직원 알림 종류** (`AlertKind`)

| 값 | 이름 | 뜻 |
|---|---|---|
| `RISK` | 위험 | 위험 신호나 즉시 위험 기준 |
| `CALL_STAFF` | 도움 요청 | 알아듣지 못함이 이어짐 |
| `USER_CALLED_STAFF` | 사람 요청 | 사용자가 직원을 찾음 |

**세션 상태** (`SessionStatus`)

| 값 | 이름 | 뜻 |
|---|---|---|
| `IN_PROGRESS` | 진행 중 | 문진 중 |
| `PAUSED_RISK` | 일시 중지(위험) | 위험으로 멈춤. 사용자 발화는 처리하지 않음 |
| `ENDED_COMPLETE` | 종료(완료) | 마침 |
| `ENDED_STAFF` | 종료(미완료: 개입 종료) | 직원이 끝냄 |
| `ENDED_LEFT` | 종료(미완료: 이탈) | 사용자가 떠남 |
| `ENDED_USER_STOP` | 종료(미완료: 사용자 중단) | 사용자가 그만둠 |

**개입 결정** (`Decision`)

| 값 | 이름 | 뜻 |
|---|---|---|
| `RESUME` | 재개 | 이어 감 |
| `END` | 종료 | 끝냄 |

**정규화 문제** (`Problem`)

| 값 | 이름 | 뜻 |
|---|---|---|
| `NO_UNIT` | 단위 없음 | 단위가 둘 이상인 슬롯에 단위 없이 숫자만 말함 |
| `OUT_OF_RANGE` | 범위 밖 | 그 단위의 범위(단위 정의의 범위)를 벗어난 값 |
| `AMBIGUOUS` | 모호함 | 범위 값이나 여러 값 |
| `MISMATCH` | 다른 답과 맞지 않음 | 선행 조건으로 이어진 다른 답과 모순 |
| `UNKNOWN_TARGET` | 정의에 없는 대상 | 문항 정의에 없는 문항·슬롯을 가리킴 |

**되물을 이유** (`Reason`)

| 값 | 이름 | 뜻 |
|---|---|---|
| `NO_UNIT` | 단위 없음 | 단위를 말해 달라 |
| `OUT_OF_RANGE` | 범위 밖 | 값이 가능한 범위를 벗어났다 |
| `AMBIGUOUS` | 모호함 | 하나로 말해 달라 |
| `MISMATCH` | 다른 답과 맞지 않음 | 앞 답과 맞지 않는다 |
| `UNRECOGNIZED` | 인식불가 | 알아듣지 못했다 |
| `MISSING_SLOT` | 필수 슬롯 누락 | 빠진 부분이 있다 |

**건너뜀 사유** (`SkipReason`)

| 값 | 이름 | 뜻 |
|---|---|---|
| `UNKNOWN_ACCEPTED` | 모름 수용 | 모름을 받아들임 |
| `REFUSAL_ACCEPTED` | 거절 수용 | 거절을 받아들임 |
| `ATTEMPTS_EXCEEDED` | 시도 초과 | 질문 상한만큼 물어도 쓸 수 있는 답이 없음 |

**흐름** (`Flow`)

| 값 | 이름 | 뜻 |
|---|---|---|
| `CONTINUE` | 계속 | 이어 감 |
| `END` | 종료 | 닫음 |

## 6. 공유 타입 사전

경계 계약 안에서 이름으로 참조되는 타입들이다(95개 정의 중 경계 계약 22개를 뺀 나머지).

#### `Action` — 행동
Plan이 이번 턴에 하기로 한 일. 한 턴에 하나.

| 값 | 이름 | 뜻 |
|---|---|---|
| `ASK_NEXT` | 다음 문항 묻기 | 열린 문항을 묻는다 |
| `ASK_MISSING` | 빠진 슬롯 되묻기 | 같은 문항의 빠진 필수 슬롯만 묻는다 |
| `ASK_CLARIFY` | 구체화 요청 | 애매한 값을 짚어 다시 묻는다 |
| `ASK_CONFIRM` | 확인 대기 확인 | 기존 답과 새 답 중 어느 것이 맞는지 묻는다 |
| `ASK_AFTER_UNKNOWN` | 모름 뒤 재질문 | 모름에 한 번 더 묻는다 |
| `ASK_AFTER_REFUSAL` | 거절 시 설명 후 재질문 | 왜 묻는지 설명하고 다시 묻는다 |
| `ASK_CORRECTION_TARGET` | 정정 구체화 | 무엇을, 어떤 값으로 고칠지 묻는다 |
| `ASK_FINISH` | 종료 확인 | 마칠지 묻는다 |
| `ASK_STOP` | 중단 확인 | 정말 그만둘지 묻는다 |
| `ASK_REPEAT` | 다시 말씀 요청 | 알아듣지 못했으니 다시 말해 달라 |
| `CALL_STAFF` | 도움 요청 | 알아듣지 못함이 이어져 직원을 부른다 |
| `REDIRECT` | 무관 안내 후 다시 묻기 | 받아 주고 하던 질문을 잇는다 |
| `RISK_NOTICE` | 위험 안내 | 위급 안내를 하고 멈춘다 |
| `WAIT_NOTICE` | 대기 안내 | 기다리겠다고 한다 |
| `STAFF_NOTICE` | 사람 연결 안내 | 직원을 불렀다고 한다 |
| `FAREWELL` | 종료 인사 | 마친다 |

#### `AlertKind` — 알림 종류
직원 알림의 까닭.

| 값 | 이름 | 뜻 |
|---|---|---|
| `RISK` | 위험 | 위험 신호나 즉시 위험 기준 |
| `CALL_STAFF` | 도움 요청 | 알아듣지 못함이 이어짐 |
| `USER_CALLED_STAFF` | 사람 요청 | 사용자가 직원을 찾음 |

#### `AskAction` — 묻기 행동
사용자에게 답을 기다리는 행동.

| 값 | 이름 | 뜻 |
|---|---|---|
| `ASK_NEXT` | 다음 문항 묻기 | 열린 문항을 묻는다 |
| `ASK_MISSING` | 빠진 슬롯 되묻기 | 같은 문항의 빠진 필수 슬롯만 묻는다 |
| `ASK_CLARIFY` | 구체화 요청 | 애매한 값을 짚어 다시 묻는다 |
| `ASK_CONFIRM` | 확인 대기 확인 | 기존 답과 새 답 중 어느 것이 맞는지 묻는다 |
| `ASK_AFTER_UNKNOWN` | 모름 뒤 재질문 | 모름에 한 번 더 묻는다 |
| `ASK_AFTER_REFUSAL` | 거절 시 설명 후 재질문 | 왜 묻는지 설명하고 다시 묻는다 |
| `ASK_CORRECTION_TARGET` | 정정 구체화 | 무엇을, 어떤 값으로 고칠지 묻는다 |
| `ASK_FINISH` | 종료 확인 | 마칠지 묻는다 |
| `ASK_STOP` | 중단 확인 | 정말 그만둘지 묻는다 |

#### `AskDirective` — 기다리는 답
다음 턴에 기다리는 답. 묻기 행동만.

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `action` | 필수 | AskAction | **행동** — 묻기 행동. |
| `targets` | 필수 | array<Target> | **대상 목록** — 묻는 대상. |
| `target_pending_id` | 필수 | PendingId \| null | **대상 확인 대기 ID** — 확인 대기 확인일 때 그 ID. |
| `say_values` | 필수 | array<SayValue> | **말할 값** — 물을 때 말한 값. |

#### `AskSubject` — 물은 대상
물은 횟수를 세는 단위: 대상(슬롯·문항) 또는 대상 없는 물음.

| 갈래 | 뜻 | 필드 (*필수) |
|---|---|---|
|  |  |  |
| 대상 없는 물음 | 대상이 없는 묻기 행동. | untargeted*: `ASK_FINISH` \| `ASK_STOP` \| `ASK_CORRECTION_TARGET` |

#### `ChangedSlot` — 값이 바뀐 슬롯
현재값이 답으로 바뀐 슬롯.

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `slot` | 필수 | SlotRef | **슬롯** — 바뀐 슬롯. |
| `previous_value` | 필수 | Value \| null | **이전 값** — 바뀌기 전 답. 없었으면 없음. |
| `new_value` | 필수 | Value | **새 값** — 바뀐 뒤 답. |
| `kind` | 필수 | `FIRST_ANSWER` \| `CORRECTION` | **종류** — 첫 답인지 고친 것인지. |

#### `CurrentValue` — 현재값
슬롯의 지금 기록: 답(값) / 모름 / 거절 / 없음.

| 갈래 | 뜻 | 필드 (*필수) |
|---|---|---|
| 답 | 확정한 답을 answer 필드로 감싼 기록. 모름·거절 표지와 구별되는 값 분기다. | answer*: Value |
| 모름 | 모름. | `UNKNOWN_RECORD` |
| 거절 | 거절. | `REFUSAL_RECORD` |
| 없음 | 아직 없음. | `NONE` |

#### `Decision` — 개입 결정 값
직원의 재개 또는 종료.

| 값 | 이름 | 뜻 |
|---|---|---|
| `RESUME` | 재개 | 이어 감 |
| `END` | 종료 | 끝냄 |

#### `Directive` — 응답 지시
LoRA-B가 이번에 말할 것 전부.

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `action` | 필수 | Action | **행동** — 이번 턴의 행동. |
| `targets` | 필수 | array<Target> | **대상 목록** — 행동의 대상. |
| `target_pending_id` | 필수 | PendingId \| null | **대상 확인 대기 ID** — 행동이 확인 대기 확인일 때. |
| `awaiting` | 필수 | AskDirective \| null | **기다리는 답** — 묻기 행동이면 자기 자신. 다시 말씀 요청·도움 요청·무관 안내·위험 안내·대기 안내·사람 연결 안내는 지금 물을 것. 종료 인사만 없음. |
| `say_values` | 필수 | array<SayValue> | **말할 값** — 말할 값들. |
| `reask_reasons` | 필수 | array<Reason> | **되물을 이유** — 판정 사유. 다시 말씀 요청이면 인식불가. |
| `notices` | 필수 | array<Notice> | **알릴 것** — 행동과 함께 알릴 것들. |
| `sentence_materials` | 필수 | SentenceMaterials | **문장 재료** — 등록 문장들. |

#### `DispatchRecord` — 전달 기록
결과 전달 한 건.

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `succeeded` | 필수 | boolean | **성공 여부** — 성공했는지. |

#### `FailedStep` — 실패한 단계
턴 결과가 실패일 때 실패한 곳 하나.

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `phase` | 필수 | `BEFORE_COMMIT` \| `AFTER_COMMIT` | **시점** — 쓰기 확정 전인지 뒤인지. |
| `step` | 필수 | `LoRA-A` \| `NORMALIZE` \| `JUDGE` \| `RECORD_WRITE` \| `PLAN` \| `COMMIT` \| `DELIVER_STAFF` \| `LoRA-B` \| `DELIVER_FRONT` | **단계** — 실패한 컴포넌트 또는 일. |

#### `FillValue` — 채울 값
안내 문장에 넣을 계산 값의 종류.

| 값 | 이름 | 뜻 |
|---|---|---|
| `REMAINING_COUNT` | 남은 문항 수 | 이번 턴 반영 뒤에 열려 있는 문항의 수. 미룬 문항은 세고, 건너뛴 문항(모름 수용·거절 수용·시도 초과)과 선행 조건이 맞지 않는 문항은 세지 않는다 |

#### `FixedSentence` — 고정 문장
종류와 문장.

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `key` | 필수 | FixedSentenceKey | **종류** — 고정 문장 종류. |
| `sentence` | 필수 | string(≤2000) | **문장** — 검토된 문장. |

#### `FixedSentenceKey` — 고정 문장 종류
세션 설정에 등록하는 고정 문장의 종류. 실제 문장 선택·생성은 담당 컴포넌트의 책임이다.

| 값 | 이름 | 뜻 |
|---|---|---|
| `ASK_REPEAT` | 다시 말씀 요청 | 다시 말씀 요청 때 쓰는 문장 |
| `OOS_NOTICE` | 무관 안내 | 문진 밖 발화에 대응하기 위한 등록 문장의 종류. 적절한 수용·지원 불가 표현의 선택은 응답 담당 컴포넌트의 책임이다. |
| `CALL_STAFF` | 도움 요청 | 도움 요청 때 쓰는 문장 |
| `FAREWELL` | 종료 인사 | 종료 인사 때 쓰는 문장 |
| `ASK_CONFIRM` | 확인 대기 확인 | 확인 대기 확인 때 쓰는 문장 |
| `ASK_CORRECTION_TARGET` | 정정 구체화 | 정정 구체화 때 쓰는 문장 |
| `ASK_FINISH` | 종료 확인 | 종료 확인 때 쓰는 문장 |
| `RISK_NOTICE` | 위험 안내 | 위험 안내 때 쓰는 문장 |
| `RESUME` | 재개 | 재개 때 쓰는 문장 |
| `SURVEY_STOPPED` | 문진 중단 | 문진 중단 때 쓰는 문장 |
| `WAIT_NOTICE` | 대기 안내 | 대기 안내 때 쓰는 문장 |
| `ASK_STOP` | 중단 확인 | 중단 확인 때 쓰는 문장 |
| `STAFF_NOTICE` | 사람 연결 안내 | 사람 연결 안내 때 쓰는 문장 |
| `DEFERRED` | 미룸 | 미룸 때 쓰는 문장 |

#### `Flow` — 흐름
이번 턴 뒤 세션을 닫을지.

| 값 | 이름 | 뜻 |
|---|---|---|
| `CONTINUE` | 계속 | 이어 감 |
| `END` | 종료 | 닫음 |

#### `GuideItem` — 안내 항목
사용자가 물을 수 있는 것과 그 답.

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `guide_id` | 필수 | string | **안내 항목 ID** — 식별자. |
| `selection_criterion` | 필수 | string(≤2000) | **고르는 기준** — LoRA-A가 볼 설명. |
| `per_question` | 필수 | boolean | **문항별** — 참이면 문장은 각 문항의 안내 문장에 있다. |
| `sentence` | 필수 | string(≤2000) \| null | **문장** — 문항별이 아니면 문장. 문항별이면 없음. |
| `fill_value` | 필수 | FillValue \| null | **채울 값** — 문장에 넣을 계산 값. 없으면 없음. |

#### `InputKind` — 입력 종류
턴을 시작한 입력.

| 값 | 이름 | 뜻 |
|---|---|---|
| `SESSION_START` | 세션 시작 신호 | 첫 접속·재접속 |
| `UTTERANCE` | 발화 | 사용자 말 |
| `INTERVENTION` | 개입 결정 | 직원의 재개·종료 |
| `SESSION_END` | 세션 종료 신호 | 사용자가 떠남 |

#### `Intent` — 의도
LoRA-A가 항목마다 붙이는, 사용자가 그 말로 하려는 일.

| 값 | 이름 | 뜻 |
|---|---|---|
| `ANSWERED_INTENT` | 답함 | 묻는 문항(또는 다른 문항)에 값을 말함 |
| `CORRECTION_MARKED` | 정정 | 앞서 한 답을 고친다는 표지와 함께 말함 |
| `CONFIRM_YES` | 확인-긍정 | 확인 질문에 "네" |
| `CONFIRM_NO` | 확인-부정 | 확인 질문에 "아니요" |
| `SAYS_UNKNOWN` | 모름 | 모른다고 함 |
| `SAYS_REFUSAL` | 거절 | 답하지 않겠다고 함 |
| `PROGRESS_OP` | 진행 조작 | 반복·대기·나중에·중단 요청 |
| `GUIDE_REQUEST` | 안내 요청 | 안내 목록에 있는 물음(뜻, 남은 수 등) |
| `USER_CALLED_STAFF` | 사람 요청 | 직원을 찾거나 시스템이 할 수 없는 요청 |
| `OUT_OF_SCOPE` | 무관 | 문진·안내 목록과 상관없는 말 |
| `UNRECOGNIZED` | 인식불가 | 무슨 말인지 알 수 없음 |
| `RISK_SIGNAL` | 위험 신호 | 지금 위급하다는 말 |

#### `InterventionResult` — 개입 결정 결과
보낸 결정이 반영됐는지.

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `session_id` | 필수 | SessionId | **세션 식별** — 어느 세션의 값인지. |
| `result` | 필수 | `APPLIED` \| `IGNORED` \| `FAILED` | **결과** — 반영 여부. |

#### `Item` — 항목
발화에서 뽑은 (대상, 값, 원문, 의도) 하나.

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `item_no` | 필수 | integer(0..1000) | **항목 번호** — 이번 턴 안에서 항목마다 붙이는 번호(0부터). |
| `target` | 필수 | Target \| null | **대상** — 무엇에 대한 말인지. 정정 의도인데 무엇을 고칠지 모르면 없음. 확인-긍정·부정·위험 신호는 없어도 된다. |
| `value` | 필수 | string(≤2000) \| null | **값** — 원문에서 뽑은 값 문자열. 표준화하지 않는다. |
| `source_text` | 필수 | SourceText | **원문 표현** — 이 항목에 해당하는 발화 부분. |
| `intent` | 필수 | Intent | **의도** — 공유 어휘 의도 중 하나. |
| `progress_op` | 필수 | ProgressOp \| null | **진행 조작** — 의도가 진행 조작일 때만. 나중에는 대상(문항 전체)이 있을 수 있다. |
| `guide_id` | 필수 | string \| null | **안내 항목 ID** — 의도가 안내 요청일 때만. 받은 안내 목록 안의 값. |

#### `ItemCheck` — 항목별 검사
항목 하나의 값을 표준화하고 검사한 사실.

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `item_no` | 필수 | integer(0..1000) | **항목 번호** — 검사한 항목. |
| `standard_value` | 필수 | Value \| null | **표준 값** — 표준화한 값. 문제가 있거나 값 없는 항목이면 없음. |
| `problems` | 필수 | array<Problem> | **문제** — 찾은 문제들(없으면 빈 목록). |
| `mismatched_slots` | 필수 | array<SlotRef> | **맞지 않는 슬롯** — 문제에 "다른 답과 맞지 않음"이 있을 때, 어느 슬롯의 값과 맞지 않는지. |
| `vs_current` | 필수 | `EQUAL` \| `DIFFERENT` \| `NO_CURRENT` \| `NOT_APPLICABLE` | **현재 값과** — 표준 값과 현재값의 비교. |
| `vs_pending` | 필수 | `EQUAL` \| `DIFFERENT` \| `NO_PENDING` \| `NOT_APPLICABLE` | **확인 대기 값과** — 표준 값과 그 슬롯 확인 대기 값의 비교. |
| `risk_rule` | 필수 | RiskResponse \| null | **위험 기준** — 표준 값이 슬롯 위험 기준에 해당하면 그 대응, 아니면 없음. |
| `prerequisite_unmet` | 필수 | boolean | **선행 불충족** — 후속 문항 항목인데 선행 답이 정해지지 않았거나, 이번 발화에서 충돌이 될 값이거나, 저장할 수 없는 경우. |

#### `Judgment` — 판정
대상 하나에 대해 이번 발화가 뜻하는 것.

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `target` | 필수 | Target | **대상** — 판정의 대상. 문항 전체 가능. |
| `status` | 필수 | JudgmentStatus \| null | **상태** — 공유 어휘 상태. 확인-긍정·부정만으로 확인 대기를 받아들이거나 버리는 판정은 없음. |
| `reasons` | 필수 | array<Reason> | **사유** — 애매·누락일 때 되물을 이유. |
| `value_now` | 필수 | Value \| null | **이번 값** — 정상·정정·충돌일 때 표준 값. |
| `said_value` | 필수 | string(≤2000) \| null | **이번에 말한 값** — 애매일 때 항목의 원문 값. 같은 슬롯의 다른 값 여럿이면 " / "로 잇는다. |
| `pending_handling` | 필수 | `CREATE` \| `ACCEPT` \| `DROP` \| `NONE` | **확인 대기 처리** — 이 판정이 그 슬롯 확인 대기에 하는 일. |
| `target_pending_ids` | 필수 | array<PendingId> | **대상 확인 대기 ID** — 받아들임·버림일 때 그 확인 대기 ID. 문항 전체 모름·거절이 여럿을 버리면 여럿. |
| `mismatched_slots` | 필수 | array<SlotRef> | **맞지 않는 슬롯** — 사유에 "다른 답과 맞지 않음"이 있을 때 상대 슬롯. |
| `risk_rule` | 필수 | RiskResponse \| null | **위험 기준** — 이번 값이 있을 때 정규화·검증의 표시를 옮긴다. |

#### `JudgmentStatus` — 상태
상태 판정이 대상마다 내린 판정.

| 값 | 이름 | 뜻 |
|---|---|---|
| `ANSWERED` | 정상 | 쓸 수 있는 값(첫 답이거나 기존과 같음) |
| `MISSING` | 누락 | 같은 문항의 필수 슬롯이 빠짐 |
| `UNCLEAR` | 애매 | 값에 문제가 있음 |
| `CONFLICT` | 충돌 | 표지 없이 기존 답과 다른 값 |
| `CORRECTION` | 정정 | 고친 값이 확정됨 |
| `UNKNOWN` | 모름 | 모름 |
| `REJECTED` | 거절 | 거절 |
| `PREREQUISITE_UNMET` | 선행 불충족 | 선행 조건이 정해지지 않았거나 맞지 않는 후속 문항에 대한 말 |

#### `LogEntry` — 대화 로그 항목
턴마다 한 건. 이번 턴에 오간 경계 값을 판단 없이 모은 것.

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `input` | 필수 | object | **입력** — 이번 턴 입력. |
| `handling` | 필수 | object \| `IGNORED` | **처리** — 처리 표의 결과. |
| `question_bank_version` | 필수 | integer(0..1000) | **문항 정의 버전** — 이 턴에 쓴 버전. |
| `turn_result` | 필수 | `COMMITTED` \| `NOT_APPLICABLE` \| object | **턴 결과** — 확정 / 실패(단계들) / 해당 없음(처리 안 함). |
| `parser_output` | 필수 | ParserOutput \| null | **LoRA-A 출력** — 이번 턴에 만들어진 것만. 없으면 없음. |
| `normalizer_output` | 필수 | NormalizerOutput \| null | **정규화·검증 출력** — 이번 턴 정규화·검증 컴포넌트의 검증된 출력. 출력 생성 전 실패하거나 수행하지 않았으면 null. |
| `judge_output` | 필수 | JudgeOutput \| null | **상태 판정 출력** — 이번 턴 상태 판정 컴포넌트의 검증된 출력. 출력 생성 전 실패하거나 수행하지 않았으면 null. |
| `record_writer_output` | 필수 | StoreResult \| null | **저장 판단 출력** — 이번 턴 저장 판단 컴포넌트의 검증된 출력. 결정이 실제 확정됐는지는 턴 결과·실패 시점으로 구분한다. |
| `directive` | 필수 | Directive \| null | **응답 지시** — 이번 턴 Plan이 만든 응답 지시. 생성되지 않았으면 null. 응답 생성·전달의 성공을 뜻하지 않는다. |
| `flow` | 필수 | Flow \| null | **흐름** — 이번 턴 Plan이 낸 CONTINUE 또는 END. Plan 출력이 없으면 null. 후속 전달 성공과는 별개다. |
| `progress_record_update` | 필수 | ProgressRecordUpdate \| null | **진행 기록 갱신** — 이번 턴 Plan이 만든 진행 기록 갱신안. 실제 반영 여부는 쓰기 확정 결과와 함께 확인한다. |
| `staff_alert` | 필수 | StaffAlert \| null | **직원 알림** — 이번 턴 Plan이 만든 직원 알림. 알림이 없거나 Plan을 만들지 못했으면 null. 전달 성패는 staff_alert_delivery로 확인한다. |
| `response_text` | 필수 | string(≤2000) \| null | **응답 문장** — 생성해 프론트에 전달하려고 한 응답 문장. 전달 실패 시 실제 청취는 보장되지 않는다. |
| `staff_alert_delivery` | 필수 | `SUCCESS` \| `FAILURE` \| `NOT_APPLICABLE` | **직원 알림 전달** — LangGraph가 알림을 전달한 결과. |
| `turn_failure_signal` | 필수 | TurnFailureSignal \| null | **턴 실패 신호** — 낸 것. 없으면 없음. |
| `intervention_result` | 필수 | InterventionResult \| null | **개입 결정 결과** — 낸 것. 없으면 없음. |

#### `Notice` — 알릴 것
행동과 함께 알릴 것 하나. 해당하지 않는 칸은 없음.

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `kind` | 필수 | NoticeKind | **종류** — 알릴 것 종류. |
| `guide_id` | 필수 | string \| null | **안내 항목 ID** — 종류가 안내일 때. |
| `question_id` | 필수 | QuestionId \| null | **문항 ID** — 안내(문항별)·미룸·정정 받았음·기존 답 유지일 때 그 문항. |
| `question_name` | 필수 | string(≤2000) \| null | **문항 이름** — 그 문항 이름. |
| `slot` | 필수 | SlotRef \| null | **슬롯** — 정정 받았음·기존 답 유지일 때 그 슬롯. |
| `previous_value` | 필수 | Value \| null | **이전 값** — 정정 받았음일 때 고치기 전 값. |
| `value` | 필수 | Value \| null | **값** — 정정 받았음·기존 답 유지의 값, 또는 안내의 채울 값(남은 문항 수는 단위 "문항"의 단위 값). |

#### `NoticeKind` — 알릴 것 종류
행동과 함께 알리는 것의 종류.

| 값 | 이름 | 뜻 |
|---|---|---|
| `CORRECTION_ACK` | 정정 받았음 | 값을 고쳤다 |
| `KEPT_PREVIOUS` | 기존 답 유지 | 기존 답을 그대로 둔다 |
| `RESUME` | 재개 | 다시 이어 간다 |
| `SURVEY_STOPPED` | 문진 중단 | 여기서 그만둔다 |
| `GUIDE` | 안내 | 안내 문장 |
| `DEFERRED` | 미룸 | 이 문항은 나중에 묻는다 |

#### `OpenRequests` — 열린 요청
사용자가 요구했고 아직 풀리지 않은 것. 다음에 물을 것이 아니라 사실이다.

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `correction_requests` | 필수 | array<object> | **정정 요청** — 값을 아직 받지 못한 고칠 요청. |
| `stop_requested` | 필수 | boolean | **중단 요청** — 그만하겠다고 했고 아직 확인하지 않음. |
| `deferred` | 필수 | array<object> | **미룸** — 나중에 묻기로 한 것. |

#### `PauseEntry` — 중지 이력 항목
일시 중지 또는 재개 한 건.

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `kind` | 필수 | PauseKind | **종류** — 중지 이력 종류. |
| `reasons` | 필수 | array<PauseReason> | **이유** — 일시 중지의 이유. 재개는 빈 목록. |

#### `PauseKind` — 중지 이력 종류
중지 이력 항목의 종류.

| 값 | 이름 | 뜻 |
|---|---|---|
| `PAUSE` | 일시 중지 | 위험으로 멈춤 |
| `RESUME` | 재개 | 직원이 이어 가게 함 |

#### `PauseReason` — 위험 이유
일시 중지의 이유 하나.

| 갈래 | 뜻 | 필드 (*필수) |
|---|---|---|
| 위험 신호 이유 | 위험한 말. | kind*: `RISK_SIGNAL`, evidence*: array<SourceText> |
| 위험 기준 이유 | 위험한 답. | kind*: `RISK_RULE`, target*: array<SlotRef> |

#### `PendingId` — 확인 대기 ID
저장 판단이 확인 대기를 둘 때 새로 만드는, 세션 안에서 겹치지 않는 값(예: UUID).

타입: string

#### `PendingRecord` — 확인 대기
확인을 기다리는 새 값.

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `pending_id` | 필수 | PendingId | **확인 대기 ID** — 이 슬롯의 현재 확인 대기를 식별하는 ID. 확인 응답을 특정 대기 값과 연결한다. |
| `value` | 필수 | Value | **값** — 새 값. |
| `risk_mark` | 필수 | RiskResponse \| null | **위험 표시** — 그 값의 위험 기준. |

#### `PlannerRecord` — Plan 기록
사실로 다시 계산할 수 없는 횟수만.

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `attempt_counts` | 필수 | array<object> | **시도 횟수** — 문항마다 쓸 수 있는 답 없이 지나간 턴 수(8-2절). |
| `confirm_counts` | 필수 | array<object> | **확인 횟수** — 슬롯마다 확인 대기 확인을 낸 횟수(반복 요청으로 다시 낸 것 제외, 대체돼도 이어 셈). |
| `unknown_counts` | 필수 | array<object> | **모름 횟수** — 문항마다 모름 판정이 나온 턴 수. |
| `refusal_counts` | 필수 | array<object> | **거절 횟수** — 문항마다 거절 판정이 나온 턴 수. |
| `unrecognized_streak` | 필수 | integer(0..1000) | **알아듣지 못한 연속** — 결과가 알아듣지 못함인 턴이 이어진 수. 응답 있음·무관만이면 0, 요청만이면 그대로. |
| `ask_counts` | 필수 | array<object> | **물은 횟수** — 정정 요청·미룸·종료 확인·중단 확인을 풀리지 않은 채 물은 횟수. |

#### `Policy` — 문항 정책
문항마다 몇 번까지 묻는지.

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `question_limit` | 필수 | integer(1..20) | **질문 상한** — 쓸 수 있는 답 없이 이 문항을 물을 수 있는 최대 횟수. |
| `unknown_accept_after` | 필수 | integer(1..20) | **모름 수용 시점** — 몇 번째 모름에서 받아들이고 넘어가는지(1이면 첫 모름에 넘어감). |
| `refusal_accept_after` | 필수 | integer(1..20) | **거절 수용 시점** — 몇 번째 거절에서 받아들이고 넘어가는지. |

#### `Prerequisite` — 선행 조건
이 문항을 묻는 조건: 다른 슬롯의 답이 이 선택지일 때만.

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `slot` | 필수 | SlotRef | **슬롯** — 선행 슬롯. |
| `value` | 필수 | string(≤2000) | **값** — 이 선택지일 때만 묻는다. |

#### `Problem` — 문제
정규화·검증이 항목 값에서 찾은 문제.

| 값 | 이름 | 뜻 |
|---|---|---|
| `NO_UNIT` | 단위 없음 | 단위가 둘 이상인 슬롯에 단위 없이 숫자만 말함 |
| `OUT_OF_RANGE` | 범위 밖 | 그 단위의 범위(단위 정의의 범위)를 벗어난 값 |
| `AMBIGUOUS` | 모호함 | 범위 값이나 여러 값 |
| `MISMATCH` | 다른 답과 맞지 않음 | 선행 조건으로 이어진 다른 답과 모순 |
| `UNKNOWN_TARGET` | 정의에 없는 대상 | 문항 정의에 없는 문항·슬롯을 가리킴 |

#### `ProgressOp` — 진행 조작
진행에 대한 요청의 종류.

| 값 | 이름 | 뜻 |
|---|---|---|
| `REPEAT` | 반복 | 다시 말해 달라 |
| `WAIT` | 대기 | 기다려 달라 |
| `LATER` | 나중에 | 이 문항은 나중에 |
| `STOP` | 중단 | 그만하겠다 |

#### `ProgressRecord` — 진행 기록
Plan만 쓰는 진행 사실.

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `last_directive` | 필수 | Directive \| null | **직전 응답 지시** — 마지막 턴의 응답 지시. 처음이면 없음. |
| `open_requests` | 필수 | OpenRequests | **열린 요청** — 열린 요청. |
| `skipped` | 필수 | array<SkipEntry> | **건너뜀** — 건너뛴 문항들. |
| `confirm_stopped` | 필수 | array<SlotRef> | **확인 중단** — 확인을 그만둔 슬롯들. 확인 대기는 남는다. |
| `session_status` | 필수 | SessionStatus | **세션 상태** — 세션 상태. |
| `pause_history` | 필수 | array<PauseEntry> | **중지 이력** — 일시 중지·재개 기록. |

#### `ProgressRecordUpdate` — 진행 기록 갱신
Plan이 진행 기록에 쓰는 것.

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `last_directive` | 필수 | Directive | **직전 응답 지시** — 이번 응답 지시 전체. |
| `open_requests` | 필수 | OpenRequests | **열린 요청** — 열린 요청의 전체 새 값. |
| `skipped_add` | 필수 | array<SkipEntry> | **건너뜀 추가** — 이번에 건너뛴 문항. |
| `skipped_remove` | 필수 | array<QuestionId> | **건너뜀 해제** — 건너뛴 문항에 이번에 기록이 바뀐 문항. |
| `confirm_stopped_add` | 필수 | array<SlotRef> | **확인 중단 추가** — 확인 상한으로 확인을 그만둔 슬롯. |
| `confirm_stopped_remove` | 필수 | array<SlotRef> | **확인 중단 해제** — 확인 대기가 이번 턴에 해소된 확인 중단 슬롯. |
| `session_status` | 필수 | SessionStatus \| null | **세션 상태** — 바꿀 때만 값, 그대로면 없음. |
| `pause_history_add` | 필수 | array<PauseEntry> | **중지 이력 추가** — 이번 턴의 일시 중지·재개. |

#### `QuestionDef` — 문항 정의
문항 하나.

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `question_id` | 필수 | QuestionId | **문항 ID** — 식별자. |
| `name` | 필수 | string(≤2000) | **이름** — 말할 때 쓰는 이름. |
| `order` | 필수 | integer(0..1000) | **순서** — 묻는 순서. |
| `prerequisite` | 필수 | Prerequisite \| null | **선행 조건** — 없으면 항상 묻는다. |
| `question_sentence` | 필수 | string(≤2000) | **문항 문장** — 물을 때의 문장. |
| `refusal_explanation` | 필수 | string(≤2000) | **거절 시 설명** — 왜 묻는지 설명하는 문장. |
| `guide_sentences` | 필수 | array<QuestionGuideSentence> | **안내 문장** — 문항별 안내 항목마다 하나(등록 규칙: 모든 문항에 있어야 등록). |
| `affected_followups` | 필수 | array<QuestionId> | **영향받는 후속 문항** — 이 문항 답이 바뀌면 무효가 되는 후속 문항. |
| `policy` | 필수 | Policy | **정책** — 문항 정책. |
| `repeat_keys` | 필수 | array<string> | **반복 키** — 이 문항이 줄마다 반복되면 쓸 수 있는 반복 키들. 반복하지 않으면 빈 목록. |
| `slots` | 필수 | array<SlotDef> | **슬롯** — 답 칸들. |

#### `QuestionGuideSentence` — 문항별 안내 문장
문항별 안내 항목의 이 문항 문장.

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `guide_id` | 필수 | string | **안내 항목 ID** — 안내 목록의 문항별 항목. |
| `sentence` | 필수 | string(≤2000) | **문장** — 등록 문장. |

#### `QuestionId` — 문항 ID
문진 설계자가 문항 정의 저장소에 정한 문항 식별자.

타입: string

#### `Reason` — 사유
되물을 때 사용자에게 짚어 줄 이유.

| 값 | 이름 | 뜻 |
|---|---|---|
| `NO_UNIT` | 단위 없음 | 단위를 말해 달라 |
| `OUT_OF_RANGE` | 범위 밖 | 값이 가능한 범위를 벗어났다 |
| `AMBIGUOUS` | 모호함 | 하나로 말해 달라 |
| `MISMATCH` | 다른 답과 맞지 않음 | 앞 답과 맞지 않는다 |
| `UNRECOGNIZED` | 인식불가 | 알아듣지 못했다 |
| `MISSING_SLOT` | 필수 슬롯 누락 | 빠진 부분이 있다 |

#### `Request` — 요청
의도가 진행 조작·안내 요청·사람 요청인 항목. 같은 것이 여럿이면 하나로 합친다.

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `kind` | 필수 | RequestKind | **종류** — 요청 종류. |
| `guide_id` | 필수 | string \| null | **안내 항목 ID** — 종류가 안내일 때. |
| `target_question_id` | 필수 | QuestionId \| null | **대상 문항 ID** — 나중에·안내의 대상 문항. 항목에 대상이 없으면 기다리는 답의 대상 문항(하나일 때). 정의에 없는 대상이었으면 없음. |
| `source_text` | 필수 | array<SourceText> | **원문 표현** — 합친 항목들의 원문. |

#### `RequestKind` — 요청 종류
발화 판정의 요청 하나의 종류.

| 값 | 이름 | 뜻 |
|---|---|---|
| `REPEAT` | 반복 | 다시 말해 달라 |
| `WAIT` | 대기 | 기다려 달라 |
| `LATER` | 나중에 | 이 문항은 나중에 |
| `STOP` | 중단 | 그만하겠다 |
| `GUIDE` | 안내 | 안내 목록의 물음 |
| `STAFF_REQUEST` | 사람 | 직원 요청 |

#### `RiskResponse` — 위험 대응
위험 기준에 해당하는 답에 할 일.

| 값 | 이름 | 뜻 |
|---|---|---|
| `IMMEDIATE` | 즉시 | 바로 멈추고 직원을 부름 |
| `ON_RESULT` | 결과 표시 | 계속하고 결과에 표시 |

#### `RiskRule` — 위험 기준
답이 위험한 조건과 대응.

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `operator` | 필수 | `=` \| `>=` | **연산** — 비교 방법. |
| `value` | 필수 | Value | **기준 값** — 비교할 값(선택지 또는 단위 값). |
| `response` | 필수 | RiskResponse | **대응** — 해당하면 할 일. |

#### `SayValue` — 말할 값
응답에서 말할 값 하나와 그 이름.

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `slot` | 필수 | SlotRef | **슬롯** — 값의 슬롯. |
| `question_name` | 필수 | string(≤2000) | **문항 이름** — 문항 정의의 문항 이름. |
| `value` | 필수 | Value | **값** — 말할 값. 역할이 이번에 말한 값이면 원문 문자열을 선택지 값 자리에 넣는다. |
| `role` | 필수 | `CURRENT` \| `PENDING` \| `JUST_SAVED` \| `SAID` | **역할** — 이 값이 무엇인지. |

#### `SentenceMaterials` — 문장 재료
이번 응답에 필요한 등록 문장 전부. 이번 행동·알릴 것·대상에 해당하는 것만 담고 나머지는 빈 목록.

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `question_sentences` | 필수 | array<object> | **문항 문장** — 대상 문항의 문항 문장. |
| `refusal_explanations` | 필수 | array<object> | **거절 시 설명** — 거절 시 설명 후 재질문의 대상 문항 설명. |
| `reask_sentences` | 필수 | array<object> | **되묻기 문장** — 대상 슬롯의 되묻기 문장. |
| `choices` | 필수 | array<object> | **선택지** — 대상 슬롯의 선택지. |
| `guide_sentences` | 필수 | array<object> | **안내 문장** — 알릴 것 안내의 문장(문항별이면 그 문항의 안내 문장, 아니면 안내 목록의 문장). |
| `fixed_sentences` | 필수 | array<object> | **고정 문장** — 이번 행동·알릴 것에 해당하는 세션 설정의 고정 문장. |

#### `SessionId` — 세션 식별
프론트가 정한 세션 식별자. 발급·인증은 API·인증 영역의 일.

타입: string

#### `SessionInfo` — 세션 정보
세션 식별과 문항 정의 버전.

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `session_id` | 필수 | SessionId | **세션 식별** — 어느 세션의 값인지. |
| `question_bank_version` | 필수 | integer(0..1000) | **문항 정의 버전** — 세션을 만들 때의 최신 버전. |

#### `SessionSettings` — 세션 설정
문항과 상관없는 설정.

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `risk_phrases` | 필수 | array<string(≤2000)> | **위험 표현 목록** — 원문에 들어 있으면 위험 신호로 보는 표현. |
| `confirm_limit` | 필수 | integer(1..20) | **확인 상한** — 같은 확인 대기를 물을 수 있는 최대 횟수. |
| `unrecognized_streak_limit` | 필수 | integer(1..20) | **알아듣지 못한 연속 상한** — 이만큼 이어지면 도움 요청. |
| `ask_limit` | 필수 | integer(1..20) | **물음 상한** — 같은 대상을 풀리지 않은 채 물을 수 있는 최대 횟수. |
| `fixed_sentences` | 필수 | array<FixedSentence> | **고정 문장** — 행동·알릴 것 종류마다 하나. 의료진이 검토해 등록한다. |
| `guide_list` | 필수 | array<GuideItem> | **안내 목록** — 안내 항목들. |

#### `SessionStatus` — 세션 상태
세션이 어디에 있는지.

| 값 | 이름 | 뜻 |
|---|---|---|
| `IN_PROGRESS` | 진행 중 | 문진 중 |
| `PAUSED_RISK` | 일시 중지(위험) | 위험으로 멈춤. 사용자 발화는 처리하지 않음 |
| `ENDED_COMPLETE` | 종료(완료) | 마침 |
| `ENDED_STAFF` | 종료(미완료: 개입 종료) | 직원이 끝냄 |
| `ENDED_LEFT` | 종료(미완료: 이탈) | 사용자가 떠남 |
| `ENDED_USER_STOP` | 종료(미완료: 사용자 중단) | 사용자가 그만둠 |

#### `SkipEntry` — 건너뜀 항목
더 묻지 않기로 한 문항과 사유.

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `question_id` | 필수 | QuestionId | **문항 ID** — 문항. |
| `reason` | 필수 | SkipReason | **사유** — 건너뜀 사유. |

#### `SkipReason` — 건너뜀 사유
문항을 더 묻지 않기로 한 까닭.

| 값 | 이름 | 뜻 |
|---|---|---|
| `UNKNOWN_ACCEPTED` | 모름 수용 | 모름을 받아들임 |
| `REFUSAL_ACCEPTED` | 거절 수용 | 거절을 받아들임 |
| `ATTEMPTS_EXCEEDED` | 시도 초과 | 질문 상한만큼 물어도 쓸 수 있는 답이 없음 |

#### `SlotDef` — 슬롯 정의
문항의 답 칸 하나.

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `slot_id` | 필수 | string | **슬롯 ID** — 문항 안의 칸 식별자. |
| `units` | 필수 | array<UnitDef> | **단위** — 단위 슬롯의 단위들. 선택지 슬롯이면 빈 목록. |
| `choices` | 필수 | array<string(≤2000)> | **선택지** — 선택지 슬롯의 선택지. 단위 슬롯이면 빈 목록. |
| `yes_no_map` | 필수 | object \| null | **네아니요 대응** — "네"·"아니요"가 이 슬롯의 어떤 선택지인지. 예/아니요로 답할 수 있는 선택 슬롯만. |
| `required` | 필수 | boolean | **필수** — 꼭 받아야 하는 칸인지. |
| `reask_sentence` | 필수 | string(≤2000) | **되묻기 문장** — 이 칸만 다시 물을 때의 문장. |
| `risk_rule` | 필수 | RiskRule \| null | **위험 기준** — 있으면 그 조건과 대응. 없으면 없음. |

#### `SlotRecord` — 슬롯 기록
슬롯 하나의 응답 기록. 저장 판단만 쓴다.

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `slot` | 필수 | SlotRef | **슬롯** — 이 답 기록이 속한 문항·반복 행·슬롯의 식별자. |
| `current_value` | 필수 | CurrentValue | **현재값** — 지금 기록. |
| `risk_mark` | 필수 | RiskResponse \| null | **위험 표시** — 현재값의 위험 기준. |
| `history` | 필수 | array<Value> | **이력** — 이전 답 값들(오래된 것부터). |
| `pending` | 필수 | PendingRecord \| null | **확인 대기** — 있으면 하나. 한 슬롯에 최대 하나(모양으로 보장). |

#### `SlotRef` — 슬롯
답 칸 하나. 문항 ID·반복 키·슬롯 ID 셋으로 가리킨다.

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `question_id` | 필수 | QuestionId | **문항 ID** — 그 슬롯이 속한 문항. |
| `repeat_key` | 필수 | string | **반복 키** — 반복 문항에서 그 줄의 식별자. 반복하지 않는 문항은 빈 문자열. |
| `slot_id` | 필수 | string | **슬롯 ID** — 문항 안의 칸 식별자. |

#### `SourceText` — 원문 표현
사용자 발화에서 그대로 옮긴 부분.

타입: string(≤2000)

#### `StaffAlert` — 직원 알림
직원을 부르는 알림.

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `kind` | 필수 | AlertKind | **종류** — 알림 종류. |
| `reasons` | 필수 | array<StaffAlertReason> | **이유** — 이유들. 도움 요청이면 빈 목록. 위험 신호와 위험 기준이 함께면 둘 다. |

#### `StaffAlertReason` — 직원 알림 이유
직원 알림의 이유 하나.

| 갈래 | 뜻 | 필드 (*필수) |
|---|---|---|
| 위험 신호 이유 | 위험한 말. | kind*: `RISK_SIGNAL`, evidence*: array<SourceText> |
| 위험 기준 이유 | 위험한 답. | kind*: `RISK_RULE`, target*: array<object> |
| 사람 요청 이유 | 직원 요청. | kind*: `USER_CALLED_STAFF`, evidence*: array<SourceText> |

#### `StoreAction` — 저장 동작
저장 판단이 슬롯마다 기록 저장소에 시키는 일.

| 값 | 이름 | 뜻 |
|---|---|---|
| `FIRST_WRITE` | 첫 저장 | 빈 슬롯에 값을 넣음 |
| `NEW_REVISION` | 새 revision | 있던 답을 고침(이전 답은 이력으로) |
| `RECORD_UNKNOWN` | 모름 기록 | 모름으로 기록 |
| `RECORD_REFUSAL` | 거절 기록 | 거절로 기록 |
| `SET_PENDING` | 확인 대기 둠 | 기존 값은 두고 새 값을 확인 대기에 둠 |
| `ACCEPT_PENDING` | 확인 대기 받아들임 | 확인 대기 값을 현재값으로 |
| `DROP_PENDING` | 확인 대기 버림 | 확인 대기를 지움 |
| `INVALIDATE` | 무효화 | 선행 답이 바뀌어 후속 답을 지움 |

#### `StoreDecision` — 저장 결정
슬롯 하나에 대한 기록 저장소 쓰기. 변경 없는 슬롯은 나오지 않는다. 무효화가 먼저 온다.

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `slot` | 필수 | SlotRef | **슬롯** — 쓸 슬롯. |
| `action` | 필수 | StoreAction | **동작** — 저장 동작. |
| `value` | 필수 | Value \| null | **값** — 첫 저장·새 revision·확인 대기 둠·확인 대기 받아들임일 때. |
| `pending_id` | 필수 | PendingId \| null | **확인 대기 ID** — 확인 대기 둠이면 새로 만든 ID, 받아들임·버림이면 그 ID. |
| `risk_mark` | 필수 | RiskResponse \| null | **위험 표시** — 값을 저장하거나 확인 대기에 두거나 받아들일 때 그 값의 위험 기준(받아들임이면 확인 대기의 위험 표시). |

#### `StoreSummary` — 저장 결과 요약
이번 저장 결정으로 무엇이 바뀌었는지.

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `changed_slots` | 필수 | array<ChangedSlot> | **값이 바뀐 슬롯** — 현재값이 답으로 바뀐 슬롯들. |
| `unknown_refused_records` | 필수 | array<object> | **모름·거절 기록** — 모름·거절로 기록된 슬롯들. |
| `created_pendings` | 필수 | array<object> | **생긴 확인 대기** — 이번에 생긴 확인 대기들. |
| `resolved_pendings` | 필수 | array<object> | **해소된 확인 대기** — 이번에 없어지거나 바뀐 확인 대기들. |
| `invalidated_questions` | 필수 | array<QuestionId> | **무효화된 문항** — 이번에 실제로 무효화한 슬롯이 있는 문항. |

#### `Target` — 대상
슬롯 하나 또는 문항 전체.

타입: SlotRef \| WholeQuestion

#### `TurnFailureSignal` — 턴 실패 신호
처리하기로 한 턴이 실패했을 때.

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `session_id` | 필수 | SessionId | **세션 식별** — 어느 세션의 값인지. |
| `write_committed` | 필수 | `COMMITTED` \| `NOT_COMMITTED` | **쓰기 확정** — 이번 턴의 쓰기가 확정됐는지. |
| `staff_alert` | 필수 | `NONE` \| `DELIVERED` \| `DELIVERY_FAILED` | **직원 알림** — 직원 알림 전달 결과. |

#### `TurnKind` — 턴 종류
LangGraph가 처리 표로 정한 이번 턴의 종류.

| 값 | 이름 | 뜻 |
|---|---|---|
| `SESSION_START` | 세션 시작 | 첫 접속·재접속 |
| `UTTERANCE` | 발화 | 사용자 말 |
| `RESUME` | 재개 | 위험 일시 중지 뒤 직원이 재개 |
| `INTERVENTION_END` | 개입 종료 | 직원이 끝냄 |
| `END_LEFT` | 이탈 종료 | 프론트가 떠났다고 알림 |

#### `UnitDef` — 단위 정의
슬롯이 받는 단위 하나.

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `name` | 필수 | string(≤2000) | **이름** — 단위 이름. 표준 값의 단위로 쓴다. |
| `synonyms` | 필수 | array<string(≤2000)> | **다른 이름** — 같은 단위를 가리키는 말(개 = 개비). |
| `range` | 필수 | array<number(-100000..100000)> \| null | **범위** — 이 단위로 센 값의 가능한 범위 [최소, 최대]. 환산이 있는 단위면 없음(환산한 단위의 범위를 쓴다). |
| `convert_to` | 필수 | object \| null | **환산** — 다른 단위로 바꿀 수 있으면 그 단위와 배수(갑 → 개비 20). 없으면 없음. |

#### `UtteranceJudgment` — 발화 판정
발화 전체에 대한 판정.

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `result` | 필수 | UtteranceResult | **결과** — 공유 어휘 발화 판정 결과. |
| `valueless_correction_requests` | 필수 | array<ValuelessCorrection> | **값 없는 정정 요청** — 정정 의도인데 값이 없는 항목마다. |
| `confirmation` | 필수 | `YES` \| `NO` \| `NONE` | **확인 응답** — 기다리는 답이 종료 확인·중단 확인·정정 구체화일 때의 승낙·거부. |
| `requests` | 필수 | array<Request> | **요청** — 요청 목록. |
| `risk_signal` | 필수 | object \| null | **위험 신호** — 의도가 위험 신호인 항목이 있거나 원문이 위험 표현 목록에 걸리면 있음. |

#### `UtteranceResult` — 발화 판정 결과
발화 전체가 무엇이었는지. 겹치지 않고 모든 경우를 덮는다.

| 값 | 이름 | 뜻 |
|---|---|---|
| `HAS_ANSWER` | 응답 있음 | 판정·확인 응답·값 없는 정정 요청·위험 신호 중 하나라도 있음 |
| `REQUEST_ONLY` | 요청만 | 위의 것은 없고 요청이 있음 |
| `OUT_OF_SCOPE_ONLY` | 무관만 | 위의 것도 요청도 없고 무관 항목이 있음 |
| `UNRECOGNIZED_TURN` | 알아듣지 못함 | 그 밖(빈 발화, 인식불가뿐) |

#### `Value` — 값
표준 값. 선택지 슬롯은 선택지 문자열, 단위 슬롯은 수와 단위.

| 갈래 | 뜻 | 필드 (*필수) |
|---|---|---|
| 선택지 값 | 슬롯 선택지 중 하나. |  |
| 단위 값 | 수와 그 단위. | amount*: number(-100000..100000), unit*: string(≤2000) |

#### `ValuelessCorrection` — 값 없는 정정 요청
고치겠다는데 값이 없는 항목 하나.

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `target` | 필수 | Target \| null | **대상** — 고칠 대상. 모르면 없음. |

#### `WholeQuestion` — 문항 전체
문항의 모든 슬롯을 한꺼번에 가리킴.

| 필드 |  | 타입 | 뜻 |
|---|---|---|---|
| `question_id` | 필수 | QuestionId | **문항 ID** — 가리키는 문항. |
| `whole_question` | 필수 | `True` | **문항 전체 표시** — 항상 true. |

## 7. 변경 방법

값의 모양은 `schemas/*.json`이 원본이고, 이 문서와 발표용 HTML은 그 Schema와 필드 설명에서 만든 파생물이다. 필드를 추가·수정할 때는 필요한 값을 보여 주는 요구사항 → Schema → 필드 설명·근거 → 입력 출처(바인딩) → 정형 예시 순으로 함께 고친다. 이 계약은 **값의 구조**만 검증한다. 어떤 발화가 어떤 의도·판정인지, 문장이 적절한지는 각 컴포넌트 구현의 책임이다.
