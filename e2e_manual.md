# E2E 매뉴얼 (e2e_manual.md)

> 담당: 송다빈(Model I/O / E2E). 작업문서의 E2E 검증 대상 — 정상 응답 / 정보 누락 / 애매한 응답 / 정정 / 충돌 / 모름 / 거절 / OOS / 문진 완료 — 와, 시점별(대화 시작·재접속·위험 중지·재개·종료·이탈) 시나리오를 담았다.

## 1. 꼭 알아둘 점

- **이 시나리오의 값은 실제 컴포넌트가 실행해서 낸 결과가 아니다.** 스키마 프로젝트의 정적 예시(케이스별 case_shapes)를 가져와, DB 상태를 저장 규칙대로 다시 계산해 만든 **기준(golden) 트레이스**다. 모델·코드·DB를 붙인 실제 실행에서 같은 형식으로 트레이스를 저장하면 같은 검사기로 검증할 수 있다(§5).
- 검사기가 보증하는 것은 **구조와 연결**이다: 계약(JSON Schema) 준수, 단계 간 값 전달의 일치, DB 저장 효과, 기대 코드(의도·판정·저장 동작·행동·흐름)의 일치. 응답 문장이 자연스러운지, 발화를 올바른 의도로 분류했는지는 검사하지 않는다.
- 시나리오 원천은 케이스 ID(`source_case`)로 추적된다. 요구사항의 출발점은 `schema-project/work/testcases/cases/`이다.

## 2. 폴더

```
schemas/                 JSON Schema 22개 (경계별, 자체 완결) + INDEX.md
tests/e2e/
  run_e2e.py             검사기 (pip install jsonschema)
  scenarios/             시나리오 18개 (e2e_*.json) + index.json
  fixtures/question_bank.json   예시 문항 정의(Q1~Q8)
  tools/build_scenarios.py      스키마 프로젝트의 case_shapes에서 시나리오를 다시 만드는 스크립트
```

## 3. 시나리오 목록

| 파일 | 이름 | 시점 | 작업문서 E2E 대상 | 원천 케이스 | 턴 | 설명 |
|---|---|---|---|---|---|---|
| `e2e_01_normal` | 정상 응답 | 발화 | 정상 응답 | B1 | 1 | 현재 문항에 대한 정상 응답. 3개 슬롯이 첫 저장되고 다음 문항(Q4)을 묻는다. |
| `e2e_02_missing` | 정보 누락 | 발화 | 정보 누락 | B2 | 1 | 필수 슬롯 일부만 답함. 받은 값은 저장하고 빠진 슬롯만 되묻는다. |
| `e2e_03_unclear` | 애매한 응답 | 발화 | 애매한 응답 | B3a | 1 | 값이 모호하거나 단위가 없음. 저장하지 않고 구체화를 요청한다. |
| `e2e_04_correction` | 정정 | 발화 | 정정 | C1 | 1 | 정정 표지가 있는 발화. 새 revision으로 저장하고 이전 값은 이력으로 넘긴다. |
| `e2e_05_conflict` | 충돌 | 발화 | 충돌 | C3 | 1 | 표지 없이 기존 값과 다른 값. 기존 값을 지키고 확인 대기에 두어 확인을 묻는다. |
| `e2e_06_unknown` | 모름 | 발화 | 모름 | B7a | 1 | 모른다는 답. 모름으로 기록하고 문항 정책에 따라 다시 묻는다. |
| `e2e_07_refusal` | 거절 | 발화 | 거절 | B8a | 1 | 답변 거부. 거절로 기록하고 왜 묻는지 설명한 뒤 다시 묻는다. |
| `e2e_08_oos` | 문진 무관(OOS) | 발화 | OOS | K1 | 1 | 문진과 무관한 말. 기록하지 않고 받아 준 뒤 하던 질문을 다시 한다. |
| `e2e_09_complete` | 문진 완료 | 발화 | 문진 완료 | H1, H2 | 2 | 마지막 문항 응답 → 종료 확인 → 승낙. 세션이 종료(완료)되고 결과 전달이 호출된다. (2턴) |
| `e2e_10_session_start` | 대화 시작 | 대화 시작 | 시점 시나리오 | A1 | 1 | 말 없이 시작 신호만 옴. 세션이 만들어지고 LoRA-A~저장 판단 없이 첫 질문을 한다. |
| `e2e_11_reconnect` | 재접속 | 대화 시작 | 시점 시나리오 | A3 | 1 | 연결이 끊겼다 다시 붙음. 하던 곳부터 다시 묻는다. |
| `e2e_12_first_utterance` | 시작 신호 없이 첫 발화 | 대화 시작 | 시점 시나리오 | A2 | 1 | 시작 버튼 없이 바로 답함. 세션을 만든 뒤 전체 흐름이 돈다. |
| `e2e_13_risk_resume` | 위험 신호 → 일시 중지 → 직원 재개 | 위험·개입 | 시점 시나리오 | G1, G6a | 2 | 위급한 말로 세션이 일시 중지되고 직원 알림이 나간다. 직원이 재개하면 하던 질문을 이어 묻는다. (2턴) |
| `e2e_14_paused_ignored` | 멈춘 동안의 발화 | 위험·개입 | 시점 시나리오 | G5 | 1 | 일시 중지(위험) 중 사용자가 말함. 어떤 컴포넌트도 부르지 않고 로그만 남긴다. |
| `e2e_15_staff_call` | 직원 호출 | 위험·개입 | 시점 시나리오 | F1 | 1 | 사용자가 직원을 찾음. 사람 연결 안내와 직원 알림. 세션은 계속 진행 중. |
| `e2e_16_user_left` | 이탈 종료 | 종료 | 시점 시나리오 | A4a | 1 | 프론트가 사용자가 떠났다고 알림. 받은 데까지 미완료로 결과가 넘어간다. |
| `e2e_17_staff_end` | 직원이 문진 종료 | 종료 | 시점 시나리오 | F4 | 1 | 직원이 종료 결정. 종료 인사와 함께 미완료로 결과가 넘어간다. |
| `e2e_18_ended_ignored` | 끝난 세션에 발화 | 종료 | 시점 시나리오 | A5 | 1 | 종료된 세션에 다음 사람이 말함. 처리도 기록도 하지 않는다. |

## 4. 트레이스 형식

시나리오 파일 하나는 `turns[]`를 갖고, 턴마다 `trace`에 **경계를 지난 값**을 단계 이름으로 담는다. 각 단계는 `{ "contract": <계약명>, "data": <값> }`이며 값은 `schemas/<계약명>.json`을 따른다. 작업문서의 Trace 순서(사용자 입력 → LoRA-A Input → LoRA-A Output → Normalization Result → DB Result → Transition Plan → LoRA-B Input → LoRA-B Output)와 대응한다.

| 단계 키 | 계약 | 의미 | 작업문서 단계 |
|---|---|---|---|
| `input_message` | FrontendMessage / InterventionDecision | 사용자 입력 | ① |
| `orchestrator_input` | OrchestratorInput | LangGraph 입력(세션 상태 포함) |  |
| `db_before` | SessionStore | DB 상태 — 턴 시작 |  |
| `lora_a_input` | UtteranceParserInput | LoRA-A Input | ② |
| `lora_a_output` | ParserOutput | LoRA-A Output | ② |
| `normalizer_input` | AnswerNormalizerInput | 정규화·검증 Input | ③ |
| `normalization_result` | NormalizerOutput | Normalization Result | ③ |
| `judge_input` | AnswerJudgeInput | 상태 판정 Input | ③ |
| `judge_output` | JudgeOutput | 상태 판정 Output(상태 = semantic_status) | ③ |
| `record_writer_input` | RecordWriterInput | 저장 판단 Input | ④ |
| `db_result` | StoreResult | DB Result(저장 결정·요약) | ④ |
| `db_after_store` | SessionStore | DB 상태 — 저장 결정 반영 뒤 (재계산) | ④ |
| `planner_input` | DialoguePlannerInput | Plan Input | ⑤ |
| `transition_plan` | PlannerOutput | Transition Plan | ⑤ |
| `staff_console_input` | StaffConsoleInput | 직원 화면 Input (알림이 있을 때) |  |
| `lora_b_input` | ResponseGeneratorInput | LoRA-B Input | ⑦ |
| `lora_b_output` | GeneratorOutput | LoRA-B Output | ⑦ |
| `frontend_input` | FrontendInput | 사용자 응답 (프론트가 읽을 값) | ⑦ |
| `orchestrator_output` | OrchestratorOutput | LangGraph 출력(턴 종류·로그·실패 신호) | ⑥ |
| `dispatch_input` | DispatchInput | 결과 전달 Input (종료 턴) |  |
| `dispatch_output` | DispatchOutput | 결과 전달 Output |  |
| `db_final` | SessionStore | DB 상태 — 턴 쓰기 반영 뒤 |  |
| `question_bank` | QuestionBank | 문항 정의 (`fixtures/question_bank.json`을 검사기가 채움) |  |

발화가 없는 턴(대화 시작·재개·종료·이탈)은 LoRA-A~저장 판단 단계가 **없다**(처리 표에 따라 건너뜀). “처리 안 함” 턴은 `orchestrator_input` · `db_before` · `orchestrator_output`만 있다.

각 턴의 `assertions[]`는 케이스의 기대값에서 뽑은 코드 단위 검사다. 연산은 `equals` · `set_equals` · `contains_subset` · `is_null`, `path`는 `단계.필드[*].필드` 형식이다.

## 5. 실행

```sh
pip install jsonschema
cd tests/e2e
python3 run_e2e.py                              # scenarios/e2e_*.json 전부
python3 run_e2e.py scenarios/e2e_01_normal.json  # 하나만
python3 run_e2e.py --trace my_capture.json       # 실제 실행에서 저장한 트레이스(같은 형식)
```

종료 코드 0이면 모두 통과. 실패하면 `[schema]` `[chain]` `[store]` `[expect]` 접두어로 어느 검사가 깨졌는지 보여 준다.

| 검사 | 내용 | 예 |
|---|---|---|
| `schema` | 모든 단계의 값이 계약의 JSON Schema를 만족한다. | 의도에 어휘 밖의 값(`UNKNOWN`) → 위반 |
| `chain` | 앞 컴포넌트가 낸 값과 뒤 컴포넌트가 받은 값이 같다(바인딩 기준). | `ParserOutput.items` ≠ `AnswerNormalizerInput.items`, Plan의 `directive` ≠ LoRA-B가 받은 `directive`, `GeneratorOutput.response_text` ≠ `FrontendInput.response_text` |
| `store` | DB 상태가 저장 규칙대로 바뀌었다. | `db_after_store` = apply(`db_before`, `store_decisions`), `db_final` = + Plan의 진행·Plan 기록 갱신 |
| `expect` | 기대 코드(의도·판정·저장 동작·Plan 행동·흐름·세션 상태·턴 종류)가 트레이스에 있다. | Plan 행동이 `ASK_NEXT`여야 하는데 `ASK_MISSING` |

검사기가 실제로 잡는지 확인하려고 Plan 행동 변경 / 어휘 밖 의도 / `db_final`에 쓰기 미반영 / LoRA-B 입력 지시 변조 4가지를 일부러 넣어 보았고 모두 실패로 잡혔다.

### 5.1 실제 컴포넌트에 연결하기

- LangGraph의 각 Node 경계에서 입력·출력을 위 `trace` 단계 이름으로 저장한다(Node 이름과 단계 키는 §4 표). 계약명은 `schemas/`의 파일명과 같다.
- 시나리오의 `input_message`와 `db_before`, `question_bank`를 입력으로 넣어 파이프라인을 돌리고, 나온 트레이스를 `--trace`로 검사한다. 정규화·상태 판정·저장 판단·Plan은 코드라 출력이 결정적이어야 하므로 `transition_plan`·`db_result`가 기준 트레이스와 같아야 한다.
- LoRA-A/B는 모델이라 기준 트레이스와 값이 다를 수 있다. LoRA-A는 `expect` 검사(의도·대상)와 정규화 이후 최종 DB 값 일치로, LoRA-B는 `response_text`가 `directive`의 `say_values`·`sentence_materials`만 쓰는지로 따로 평가한다(이 검사기 범위 밖).
- 모델 출력이 깨지는 경우는 대체 출력 규칙이 있다(LoRA-A: 빈 목록·인식불가, LoRA-B: `is_fallback=true`). 이 경로는 현재 시나리오에 없고, 스키마 프로젝트의 J7 계열 케이스로 같은 방식으로 만들 수 있다.

### 5.2 시나리오 다시 만들기 / 추가하기

`tools/build_scenarios.py <schema-project 경로>`가 케이스 ID 목록에서 시나리오를 만든다. 새 시나리오는 파일 맨 위 `SCENARIOS` 목록에 `(파일명, 제목, 분류, 시점, [케이스 ID], 설명)`을 추가한다. 만들 때 두 가지 보정을 한다: ① 새 세션의 `db_before`를 세션 초기값으로 교체, ② 단계마다 달랐던 임시 확인 대기 ID를 하나로 통일. 보정한 턴은 `fixture_notes`에 적힌다.

## 6. 시나리오별 기대 흐름

### 정상 응답 — `e2e_01_normal`  
시점: 발화 · 원천 케이스: B1  
현재 문항에 대한 정상 응답. 3개 슬롯이 첫 저장되고 다음 문항(Q4)을 묻는다.

- **턴 1** (B1) 발화 “일주일에 두 번, 소주 한 병씩요”
  - 흐름: 의도 ANSWERED_INTENT → 판정 ANSWERED → 발화 판정 HAS_ANSWER → 저장 FIRST_WRITE → Plan ASK_NEXT, 흐름 CONTINUE
  - 응답(예시): “한 번에 소주 한 병 넘게 드시는 일이 있나요?”

### 정보 누락 — `e2e_02_missing`  
시점: 발화 · 원천 케이스: B2  
필수 슬롯 일부만 답함. 받은 값은 저장하고 빠진 슬롯만 되묻는다.

- **턴 1** (B2) 발화 “소주 마셔요”
  - 흐름: 의도 ANSWERED_INTENT → 판정 ANSWERED, MISSING → 발화 판정 HAS_ANSWER → 저장 FIRST_WRITE → Plan ASK_MISSING, 흐름 CONTINUE
  - 응답(예시): “음주 상세 소주. 일주일이나 한 달에 몇 번 드시는지 말씀해 주세요. 한 번에 얼마나 드시는지 말씀해 주세요.”

### 애매한 응답 — `e2e_03_unclear`  
시점: 발화 · 원천 케이스: B3a  
값이 모호하거나 단위가 없음. 저장하지 않고 구체화를 요청한다.

- **턴 1** (B3a) 발화 “서른 시간이요”
  - 흐름: 의도 ANSWERED_INTENT → 판정 UNCLEAR → 발화 판정 HAS_ANSWER → 저장 없음 → Plan ASK_CLARIFY, 흐름 CONTINUE
  - 응답(예시): “수면 서른 시간. 하루에 몇 시간 주무시는지 말씀해 주세요.”

### 정정 — `e2e_04_correction`  
시점: 발화 · 원천 케이스: C1  
정정 표지가 있는 발화. 새 revision으로 저장하고 이전 값은 이력으로 넘긴다.

- **턴 1** (C1) 발화 “아까 열 개 아니고 스무 개요”
  - 흐름: 의도 CORRECTION_MARKED → 판정 CORRECTION → 발화 판정 HAS_ANSWER → 저장 NEW_REVISION → Plan ASK_NEXT + 알릴 것 CORRECTION_ACK, 흐름 CONTINUE
  - 응답(예시): “흡연량 10개비 → 20개비. 하루에 몇 시간 주무세요?”

### 충돌 — `e2e_05_conflict`  
시점: 발화 · 원천 케이스: C3  
표지 없이 기존 값과 다른 값. 기존 값을 지키고 확인 대기에 두어 확인을 묻는다.

- **턴 1** (C3) 발화 “담배는 스무 개 피워요”
  - 흐름: 의도 ANSWERED_INTENT → 판정 CONFLICT → 발화 판정 HAS_ANSWER → 저장 SET_PENDING → Plan ASK_CONFIRM, 흐름 CONTINUE
  - 응답(예시): “어느 쪽이 맞는지 말씀해 주세요. 흡연량 10개비. 흡연량 20개비.”
  - 보정: 확인 대기 ID 표기 통일: X→N1 (예시 데이터가 단계마다 다른 임시 ID를 썼다)

### 모름 — `e2e_06_unknown`  
시점: 발화 · 원천 케이스: B7a  
모른다는 답. 모름으로 기록하고 문항 정책에 따라 다시 묻는다.

- **턴 1** (B7a) 발화 “혈압은 잘 모르겠어요”
  - 흐름: 의도 SAYS_UNKNOWN → 판정 UNKNOWN → 발화 판정 HAS_ANSWER → 저장 RECORD_UNKNOWN → Plan ASK_AFTER_UNKNOWN, 흐름 CONTINUE
  - 응답(예시): “최근에 재신 혈압이 어떻게 되세요?”

### 거절 — `e2e_07_refusal`  
시점: 발화 · 원천 케이스: B8a  
답변 거부. 거절로 기록하고 왜 묻는지 설명한 뒤 다시 묻는다.

- **턴 1** (B8a) 발화 “그건 말 안 할래요”
  - 흐름: 의도 SAYS_REFUSAL → 판정 REJECTED → 발화 판정 HAS_ANSWER → 저장 RECORD_REFUSAL → Plan ASK_AFTER_REFUSAL, 흐름 CONTINUE
  - 응답(예시): “답하기 어려우시면 넘어가셔도 됩니다. 도움을 드릴 수 있어 여쭙습니다. 최근에 죽고 싶다는 생각을 하신 적이 있나요?”

### 문진 무관(OOS) — `e2e_08_oos`  
시점: 발화 · 원천 케이스: K1  
문진과 무관한 말. 기록하지 않고 받아 준 뒤 하던 질문을 다시 한다.

- **턴 1** (K1) 발화 “고마워요”
  - 흐름: 의도 OUT_OF_SCOPE → 발화 판정 OUT_OF_SCOPE_ONLY → 저장 없음 → Plan REDIRECT, 흐름 CONTINUE
  - 응답(예시): “네, 감사합니다. 하루에 몇 시간 주무세요?”

### 문진 완료 — `e2e_09_complete`  
시점: 발화 · 원천 케이스: H1, H2  
마지막 문항 응답 → 종료 확인 → 승낙. 세션이 종료(완료)되고 결과 전달이 호출된다. (2턴)

- **턴 1** (H1) 발화 “주 세 번이요”
  - 흐름: 의도 ANSWERED_INTENT → 판정 ANSWERED → 발화 판정 HAS_ANSWER → 저장 FIRST_WRITE → Plan ASK_FINISH, 흐름 CONTINUE
  - 응답(예시): “다 여쭤봤습니다. 이대로 마칠까요?”
- **턴 2** (H2) 발화 “네”
  - 흐름: 의도 CONFIRM_YES → 발화 판정 HAS_ANSWER → 저장 없음 → Plan FAREWELL, 흐름 END → 세션 상태 → ENDED_COMPLETE
  - 응답(예시): “문진이 끝났습니다. 수고하셨습니다.”

### 대화 시작 — `e2e_10_session_start`  
시점: 대화 시작 · 원천 케이스: A1  
말 없이 시작 신호만 옴. 세션이 만들어지고 LoRA-A~저장 판단 없이 첫 질문을 한다.

- **턴 1** (A1) 입력 `SESSION_START`
  - 흐름: Plan ASK_NEXT, 흐름 CONTINUE
  - 응답(예시): “담배는 피우시나요?”
  - 보정: 새 세션이므로 db_before를 세션 초기값(규칙 9-2)으로 교체했다(예시 원본의 initial_state는 턴 처리 뒤 값이었다).

### 재접속 — `e2e_11_reconnect`  
시점: 대화 시작 · 원천 케이스: A3  
연결이 끊겼다 다시 붙음. 하던 곳부터 다시 묻는다.

- **턴 1** (A3) 입력 `SESSION_START`
  - 흐름: Plan ASK_NEXT, 흐름 CONTINUE
  - 응답(예시): “하루에 몇 개비나 피우세요?”

### 시작 신호 없이 첫 발화 — `e2e_12_first_utterance`  
시점: 대화 시작 · 원천 케이스: A2  
시작 버튼 없이 바로 답함. 세션을 만든 뒤 전체 흐름이 돈다.

- **턴 1** (A2) 발화 “담배 안 피워요”
  - 흐름: 의도 ANSWERED_INTENT → 판정 ANSWERED → 발화 판정 HAS_ANSWER → 저장 FIRST_WRITE → Plan ASK_NEXT, 흐름 CONTINUE
  - 응답(예시): “술은 드시나요?”
  - 보정: 새 세션이므로 db_before를 세션 초기값(규칙 9-2)으로 교체했다(예시 원본의 initial_state는 턴 처리 뒤 값이었다).

### 위험 신호 → 일시 중지 → 직원 재개 — `e2e_13_risk_resume`  
시점: 위험·개입 · 원천 케이스: G1, G6a  
위급한 말로 세션이 일시 중지되고 직원 알림이 나간다. 직원이 재개하면 하던 질문을 이어 묻는다. (2턴)

- **턴 1** (G1) 발화 “숨이 안 쉬어져요”
  - 흐름: 의도 RISK_SIGNAL → 발화 판정 HAS_ANSWER → 저장 없음 → Plan RISK_NOTICE, 흐름 CONTINUE → 세션 상태 → PAUSED_RISK → 직원 알림 RISK
  - 응답(예시): “바로 직원을 불렀습니다. 그 자리에 계셔 주세요.”
- **턴 2** (G6a) 입력 `RESUME`
  - 흐름: Plan ASK_NEXT + 알릴 것 RESUME, 흐름 CONTINUE → 세션 상태 → IN_PROGRESS
  - 응답(예시): “다시 이어서 여쭙겠습니다. 하루에 몇 시간 주무세요?”

### 멈춘 동안의 발화 — `e2e_14_paused_ignored`  
시점: 위험·개입 · 원천 케이스: G5  
일시 중지(위험) 중 사용자가 말함. 어떤 컴포넌트도 부르지 않고 로그만 남긴다.

- **턴 1** (G5) 발화 “언제 와요?”
  - 흐름: (LangGraph 처리 안 함 — 어떤 컴포넌트도 부르지 않음)

### 직원 호출 — `e2e_15_staff_call`  
시점: 위험·개입 · 원천 케이스: F1  
사용자가 직원을 찾음. 사람 연결 안내와 직원 알림. 세션은 계속 진행 중.

- **턴 1** (F1) 발화 “직원 좀 불러 주세요”
  - 흐름: 의도 USER_CALLED_STAFF → 발화 판정 REQUEST_ONLY → 저장 없음 → Plan STAFF_NOTICE, 흐름 CONTINUE → 직원 알림 USER_CALLED_STAFF
  - 응답(예시): “직원을 불러 드렸습니다. 문진은 이어서 하겠습니다.”

### 이탈 종료 — `e2e_16_user_left`  
시점: 종료 · 원천 케이스: A4a  
프론트가 사용자가 떠났다고 알림. 받은 데까지 미완료로 결과가 넘어간다.

- **턴 1** (A4a) 입력 `SESSION_END`
  - 흐름: Plan FAREWELL + 알릴 것 SURVEY_STOPPED, 흐름 END → 세션 상태 → ENDED_LEFT
  - 응답(예시): “문진을 여기서 마치겠습니다. 문진이 끝났습니다. 수고하셨습니다.”

### 직원이 문진 종료 — `e2e_17_staff_end`  
시점: 종료 · 원천 케이스: F4  
직원이 종료 결정. 종료 인사와 함께 미완료로 결과가 넘어간다.

- **턴 1** (F4) 입력 `END`
  - 흐름: Plan FAREWELL + 알릴 것 SURVEY_STOPPED, 흐름 END → 세션 상태 → ENDED_STAFF
  - 응답(예시): “문진을 여기서 마치겠습니다. 문진이 끝났습니다. 수고하셨습니다.”

### 끝난 세션에 발화 — `e2e_18_ended_ignored`  
시점: 종료 · 원천 케이스: A5  
종료된 세션에 다음 사람이 말함. 처리도 기록도 하지 않는다.

- **턴 1** (A5) 발화 “저 담배 안 피워요”
  - 흐름: (LangGraph 처리 안 함 — 어떤 컴포넌트도 부르지 않음)

## 7. 예시 데이터에서 발견한 불일치

스키마 프로젝트의 케이스 예시 216건(236턴)을 같은 검사기로 돌려 보았다(위 §5.2의 두 보정을 적용한 뒤). 스키마 자체의 결함은 아니지만, **예시 데이터를 기준값으로 쓰기 전에 고쳐야 할 곳**이다.

| 항목 | 내용 | 해당 케이스 |
|---|---|---|
| 저장 반영 뒤 상태 예시 | `SessionStore`의 `processing_state`(저장 결정 반영 뒤) 예시 229건 중 223건이 **저장 전(`initial_state`)과 완전히 같다**. 저장 결정이 반영되지 않은 값이라 “저장 반영 뒤” 시점의 값으로 쓸 수 없다. (Plan 입력의 `answer_records`가 실제 반영 뒤 값이며, 저장 규칙으로 재계산한 값과 213건 중 203건이 일치, 나머지 10건은 아래 확인 대기 ID 표기 차이뿐이다.) 이 폴더의 시나리오는 재계산한 값을 쓴다. | 전체 |
| 확인 대기 ID 표기 | 저장 결정의 `pending_id`("X"/"Y"/"Z")와 이후 단계·스냅샷의 ID("N1"/"N2")가 다르다. | C3, C11, G10, H3e, J7d, N6, N13, S2e, S4a, S8c |
| 판정 단계 간 불일치 | 상태 판정 출력의 `judgments`와 저장 판단·Plan이 받은 `judgments`가 다르다(대상 슬롯 자체가 다른 경우 포함). | S6a, S6b, S8b (그 외 ID 표기: G10#2, N13#2, S2e#2) |
| Plan → LoRA-B | Plan이 낸 `directive`와 LoRA-B가 받은 `directive`가 다르다(확인 대기 ID 외 차이는 H3e#2, N13#2). | H3e#2, N13#2 (그 외 ID 표기) |
| 턴 시작 상태 | `confirm_stopped` / `skipped` 값이 저장소 예시와 Plan 입력에서 다르다. | C8a, N6 (확인 중단), S3b (건너뜀 사유) |
| 새 세션 초기 상태 | 세션이 없는 턴인데 `initial_state`가 턴 처리 뒤의 값(직전 응답 지시가 이미 있음)이다. | A1, A2, D1b, N1a~N1c, J8a |
| 쓰기 실패 턴 | J8f(쓰기 확정 실패)의 최종 상태가 “아무것도 반영 안 됨”과 다르다. | J8f |

위 목록은 `tests/e2e/tools/build_scenarios.py`의 로직과 `run_e2e.py`를 전체 케이스에 돌려 얻은 것이다(236턴 중 224턴 통과, 12턴이 위 항목 때문에 실패). 실제 E2E를 붙이기 전에 케이스 예시를 고치거나 해당 케이스를 기준 트레이스에서 제외하는 것을 권한다.
