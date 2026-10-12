import json, sys, copy, re
from pathlib import Path
# 사용법: python3 build_scenarios.py <schema-project 경로>
if len(sys.argv) < 2:
    sys.exit('사용법: python3 build_scenarios.py <schema-project 경로>')
SP = Path(sys.argv[1]).resolve()
OUT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SP)); sys.path.insert(0, str(OUT))
import spec_sources as S
import run_e2e as R

cases = {c['id']: c for c in S.cases()['cases']}
sit = {s['id']: s for s in S.cases()['상황목록']}

STAGES = [
 ('input_message', None, None),
 ('orchestrator_input', 'OrchestratorInput', 'input'),
 ('db_before', 'SessionStore', 'initial_state'),
 ('lora_a_input', 'UtteranceParserInput', 'input'),
 ('lora_a_output', 'ParserOutput', 'output'),
 ('normalizer_input', 'AnswerNormalizerInput', 'input'),
 ('normalization_result', 'NormalizerOutput', 'output'),
 ('judge_input', 'AnswerJudgeInput', 'input'),
 ('judge_output', 'JudgeOutput', 'output'),
 ('record_writer_input', 'RecordWriterInput', 'input'),
 ('db_result', 'StoreResult', 'output'),
 ('db_after_store', None, None),
 ('planner_input', 'DialoguePlannerInput', 'input'),
 ('transition_plan', 'PlannerOutput', 'output'),
 ('staff_console_input', 'StaffConsoleInput', 'output'),
 ('lora_b_input', 'ResponseGeneratorInput', 'input'),
 ('lora_b_output', 'GeneratorOutput', 'output'),
 ('frontend_input', 'FrontendInput', 'output'),
 ('orchestrator_output', 'OrchestratorOutput', 'output'),
 ('dispatch_input', 'DispatchInput', 'output'),
 ('dispatch_output', 'DispatchOutput', 'output'),
 ('db_final', 'SessionStore', 'final_state'),
]
STAGE_LABEL = {
 'input_message':'사용자 입력(프론트/직원 화면)', 'orchestrator_input':'LangGraph 입력', 'db_before':'DB 상태(턴 시작)',
 'lora_a_input':'LoRA-A Input','lora_a_output':'LoRA-A Output','normalizer_input':'정규화·검증 Input',
 'normalization_result':'Normalization Result','judge_input':'상태 판정 Input','judge_output':'상태 판정 Output',
 'record_writer_input':'저장 판단 Input','db_result':'DB Result(저장 결정·요약)','db_after_store':'DB 상태(저장 결정 반영 뒤)',
 'planner_input':'Plan Input','transition_plan':'Transition Plan','staff_console_input':'직원 화면 Input',
 'lora_b_input':'LoRA-B Input','lora_b_output':'LoRA-B Output','frontend_input':'사용자 응답(프론트 Input)',
 'orchestrator_output':'LangGraph 출력(턴 종류·로그)','dispatch_input':'결과 전달 Input','dispatch_output':'결과 전달 Output',
 'db_final':'DB 상태(턴 쓰기 반영 뒤)'}

SCENARIOS = [
 ('e2e_01_normal','정상 응답','ANSWERED','발화',['B1'],'현재 문항에 대한 정상 응답. 3개 슬롯이 첫 저장되고 다음 문항(Q4)을 묻는다.'),
 ('e2e_02_missing','정보 누락','MISSING','발화',['B2'],'필수 슬롯 일부만 답함. 받은 값은 저장하고 빠진 슬롯만 되묻는다.'),
 ('e2e_03_unclear','애매한 응답','UNCLEAR','발화',['B3a'],'값이 모호하거나 단위가 없음. 저장하지 않고 구체화를 요청한다.'),
 ('e2e_04_correction','정정','CORRECTION','발화',['C1'],'정정 표지가 있는 발화. 새 revision으로 저장하고 이전 값은 이력으로 넘긴다.'),
 ('e2e_05_conflict','충돌','CONFLICT','발화',['C3'],'표지 없이 기존 값과 다른 값. 기존 값을 지키고 확인 대기에 두어 확인을 묻는다.'),
 ('e2e_06_unknown','모름','UNKNOWN','발화',['B7a'],'모른다는 답. 모름으로 기록하고 문항 정책에 따라 다시 묻는다.'),
 ('e2e_07_refusal','거절','REJECTED','발화',['B8a'],'답변 거부. 거절로 기록하고 왜 묻는지 설명한 뒤 다시 묻는다.'),
 ('e2e_08_oos','문진 무관(OOS)','OOS','발화',['K1'],'문진과 무관한 말. 기록하지 않고 받아 준 뒤 하던 질문을 다시 한다.'),
 ('e2e_09_complete','문진 완료','COMPLETE','발화',['H1','H2'],'마지막 문항 응답 → 종료 확인 → 승낙. 세션이 종료(완료)되고 결과 전달이 호출된다. (2턴)'),
 ('e2e_10_session_start','대화 시작','SESSION_START','대화 시작',['A1'],'말 없이 시작 신호만 옴. 세션이 만들어지고 LoRA-A~저장 판단 없이 첫 질문을 한다.'),
 ('e2e_11_reconnect','재접속','SESSION_START','대화 시작',['A3'],'연결이 끊겼다 다시 붙음. 하던 곳부터 다시 묻는다.'),
 ('e2e_12_first_utterance','시작 신호 없이 첫 발화','UTTERANCE','대화 시작',['A2'],'시작 버튼 없이 바로 답함. 세션을 만든 뒤 전체 흐름이 돈다.'),
 ('e2e_13_risk_resume','위험 신호 → 일시 중지 → 직원 재개','RISK','위험·개입',['G1','G6a'],'위급한 말로 세션이 일시 중지되고 직원 알림이 나간다. 직원이 재개하면 하던 질문을 이어 묻는다. (2턴)'),
 ('e2e_14_paused_ignored','멈춘 동안의 발화','IGNORED','위험·개입',['G5'],'일시 중지(위험) 중 사용자가 말함. 어떤 컴포넌트도 부르지 않고 로그만 남긴다.'),
 ('e2e_15_staff_call','직원 호출','STAFF_REQUEST','위험·개입',['F1'],'사용자가 직원을 찾음. 사람 연결 안내와 직원 알림. 세션은 계속 진행 중.'),
 ('e2e_16_user_left','이탈 종료','END_LEFT','종료',['A4a'],'프론트가 사용자가 떠났다고 알림. 받은 데까지 미완료로 결과가 넘어간다.'),
 ('e2e_17_staff_end','직원이 문진 종료','INTERVENTION_END','종료',['F4'],'직원이 종료 결정. 종료 인사와 함께 미완료로 결과가 넘어간다.'),
 ('e2e_18_ended_ignored','끝난 세션에 발화','IGNORED','종료',['A5'],'종료된 세션에 다음 사람이 말함. 처리도 기록도 하지 않는다.'),
]

def parse_target(s):
    if s is None: return None
    if '.' in s:
        q, slot = s.split('.', 1)
        if slot == '*': return {'question_id': q, 'whole_question': True}
        return {'question_id': q, 'slot_id': slot}
    return {'question_id': s, 'whole_question': True}

def pending_alias_fix(turn, trace):
    """Unify placeholder ids ('X','Y','Z') with the ids in the planner-input snapshot (same slot)."""
    if 'db_result' not in trace or 'planner_input' not in trace: return []
    snap = {R._key(r['slot']): r['pending']['pending_id'] for r in trace['planner_input']['data']['answer_records'] if r['pending']}
    mapping = {}
    for d in trace['db_result']['data']['store_decisions']:
        if d['action'] == 'SET_PENDING' and R._key(d['slot']) in snap and d['pending_id'] != snap[R._key(d['slot'])]:
            mapping[d['pending_id']] = snap[R._key(d['slot'])]
    if not mapping: return []
    def walk(n):
        if isinstance(n, dict):
            for k, v in list(n.items()):
                if k in ('pending_id', 'target_pending_id') and v in mapping: n[k] = mapping[v]
                elif k == 'target_pending_ids' and isinstance(v, list): n[k] = [mapping.get(x, x) for x in v]
                else: walk(v)
        elif isinstance(n, list):
            for x in n: walk(x)
    for st in trace.values(): walk(st['data'])
    return [f'{a}→{b}' for a, b in mapping.items()]

def build_assertions(case, trace):
    ex = case.get('expect', {}); out = []
    n = 0
    def add(desc, path, op, value, src):
        nonlocal n; n += 1
        out.append({'id': f'a{n:02d}', 'desc': desc, 'path': path, 'op': op, 'value': value, 'source': src})
    for i, it in enumerate(ex.get('LoRA-A') or []):
        want = {'intent': it['의도']}
        t = parse_target(it.get('대상'))
        if t: want['target'] = t
        add(f"LoRA-A 항목: 의도 {it['의도']}" + (f" → {it.get('대상')}" if it.get('대상') else ''), 'lora_a_output.items', 'contains_subset', [want], f'/expect/LoRA-A/{i}')
    for i, j in enumerate(ex.get('판정') or []):
        want = {'status': j['상태']}
        t = parse_target(j.get('대상'))
        if t: want['target'] = t
        add(f"판정: {j.get('대상')} {j['상태']}", 'judge_output.judgments', 'contains_subset', [want], f'/expect/판정/{i}')
    for i, s in enumerate(ex.get('저장') or []):
        want = {'action': s['동작']}
        t = parse_target(s.get('슬롯'))
        if t: want['slot'] = t
        add(f"저장 결정: {s.get('슬롯')} {s['동작']}", 'db_result.store_decisions', 'contains_subset', [want], f'/expect/저장/{i}')
    p = ex.get('Plan') or {}
    if p.get('행동'): add(f"Transition Plan 행동 {p['행동']}", 'transition_plan.directive.action', 'equals', p['행동'], '/expect/Plan/행동')
    if p.get('대상'):
        add('Plan 대상 ' + ','.join(p['대상']), 'transition_plan.directive.targets', 'contains_subset', [parse_target(q) for q in p['대상']], '/expect/Plan/대상')
    if p.get('세션상태'): add(f"세션 상태 → {p['세션상태']}", 'transition_plan.progress_record_update.session_status', 'equals', p['세션상태'], '/expect/Plan/세션상태')
    if p.get('흐름'): add(f"흐름 {p['흐름']}", 'transition_plan.flow', 'equals', p['흐름'], '/expect/Plan/흐름')
    lg = ex.get('LangGraph') or {}
    if lg.get('턴종류'): add(f"턴 종류 {lg['턴종류']}", 'orchestrator_output.turn_kind', 'equals', lg['턴종류'], '/expect/LangGraph/턴종류')
    if '결과전달호출' in lg: add(f"결과 전달 호출 {lg['결과전달호출']}", 'orchestrator_output.dispatch_called', 'equals', lg['결과전달호출'], '/expect/LangGraph/결과전달호출')
    return out

def extra_assertions(case_id, trace, out):
    n = len(out)
    def add(desc, path, op, value):
        nonlocal n; n += 1
        out.append({'id': f'a{n:02d}', 'desc': desc, 'path': path, 'op': op, 'value': value, 'source': '/expect/LangGraph (처리 안 함)'})
    if case_id == 'G5':
        add('처리 안 함: 턴 종류 없음', 'orchestrator_output.turn_kind', 'is_null', True)
        add('처리 안 함이지만 로그는 남는다(일시 중지 열)', 'orchestrator_output.log_entry.handling', 'equals', 'IGNORED')
        add('결과 전달을 부르지 않는다', 'orchestrator_output.dispatch_called', 'equals', False)
    if case_id == 'A5':
        add('처리 안 함: 턴 종류 없음', 'orchestrator_output.turn_kind', 'is_null', True)
        add('종료된 세션에는 로그도 남기지 않는다', 'orchestrator_output.log_entry', 'is_null', True)
        add('결과 전달을 부르지 않는다', 'orchestrator_output.dispatch_called', 'equals', False)

def build_turn(case_id, turn_no, tnum):
    w = json.load(open(SP / f'work/testcases/case_shapes/{case_id}.json'))
    by = {(s['turn'], s['contract'], s['role']): s['data'] for s in w['specimens']}
    case = cases[case_id]
    trace = {}
    for key, contract, role in STAGES:
        if key == 'input_message':
            if (turn_no, 'FrontendMessage', 'input') in by:
                trace[key] = {'contract': 'FrontendMessage', 'data': by[(turn_no, 'FrontendMessage', 'input')]}
            elif (turn_no, 'InterventionDecision', 'input') in by:
                trace[key] = {'contract': 'InterventionDecision', 'data': by[(turn_no, 'InterventionDecision', 'input')]}
            continue
        if key == 'db_after_store':
            if 'db_result' in trace and 'db_before' in trace:
                st = copy.deepcopy(trace['db_before']['data'])
                st['answer_records'] = R.apply_store_decisions(st['answer_records'], trace['db_result']['data']['store_decisions'])
                trace[key] = {'contract': 'SessionStore', 'data': st}
            continue
        if (turn_no, contract, role) in by:
            trace[key] = {'contract': contract, 'data': copy.deepcopy(by[(turn_no, contract, role)])}
    fixes = []
    oi = trace.get('orchestrator_input', {}).get('data')
    if oi and oi['session_found'] is False and 'db_before' in trace:
        st = trace['db_before']['data']
        created = trace['orchestrator_output']['data']['session_info_created']
        st['session_info'] = created
        for r in st['answer_records']:
            r['current_value'] = 'NONE'; r['risk_mark'] = None; r['history'] = []; r['pending'] = None
        st['progress_record'] = {'last_directive': None, 'open_requests': {'correction_requests': [], 'stop_requested': False, 'deferred': []},
                                 'skipped': [], 'confirm_stopped': [], 'session_status': 'IN_PROGRESS', 'pause_history': []}
        st['planner_record'] = {'attempt_counts': [], 'confirm_counts': [], 'unknown_counts': [], 'refusal_counts': [], 'unrecognized_streak': 0, 'ask_counts': []}
        st['dialogue_log'] = []; st['dispatch_log'] = []
        fixes.append('새 세션이므로 db_before를 세션 초기값(규칙 9-2)으로 교체했다(예시 원본의 initial_state는 턴 처리 뒤 값이었다).')
    alias = pending_alias_fix(tnum, trace)
    # keep stage order
    return {'turn': tnum, 'source_case': case_id, 'situation': {k: sit[k]['상황'] for k in case['상황'] if k in sit},
            'utterance': (trace.get('input_message', {}).get('data') or {}).get('utterance'),
            'trace': trace, 'assertions': (lambda a: (extra_assertions(case_id, trace, a), a)[1])(build_assertions(case, trace)),
            'fixture_notes': fixes + ([f'확인 대기 ID 표기 통일: {", ".join(alias)} (예시 데이터가 단계마다 다른 임시 ID를 썼다)'] if alias else [])}

def main():
    qb = None
    index = []
    for sid, title, status, timing, case_ids, desc in SCENARIOS:
        turns = []
        for i, cid in enumerate(case_ids, 1):
            w = json.load(open(SP / f'work/testcases/case_shapes/{cid}.json'))
            tn = sorted({s['turn'] for s in w['specimens']})
            assert len(tn) == 1, (cid, tn)
            t = build_turn(cid, tn[0], i)
            if qb is None:
                for s in w['specimens']:
                    if s['contract'] == 'QuestionBank' and s['role'] == 'configuration': qb = s['data']
            turns.append(t)
        sc = {'scenario_id': sid, 'title': title, 'category': status, 'timing': timing, 'description': desc,
              'source_cases': case_ids,
              'provenance': '정적 예시: 스키마 프로젝트의 case_shapes에서 가져와 저장 규칙(rules 9-2)대로 DB 상태를 재계산해 만들었다. 실제 컴포넌트 실행 결과가 아니다.',
              'question_bank_ref': '../fixtures/question_bank.json',
              'stage_labels': STAGE_LABEL, 'turns': turns}
        (OUT / 'scenarios').mkdir(parents=True, exist_ok=True)
        (OUT / 'scenarios' / f'{sid}.json').write_text(json.dumps(sc, ensure_ascii=False, indent=2), encoding='utf-8')
        index.append({'scenario_id': sid, 'title': title, 'category': status, 'timing': timing, 'turns': len(turns), 'source_cases': case_ids})
    (OUT / 'fixtures').mkdir(parents=True, exist_ok=True)
    (OUT / 'fixtures' / 'question_bank.json').write_text(json.dumps(qb, ensure_ascii=False, indent=2), encoding='utf-8')
    (OUT / 'scenarios' / 'index.json').write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding='utf-8')
    print(len(index), 'scenarios')

main()
