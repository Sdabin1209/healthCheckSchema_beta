# 공통 타입 스키마 (types/)

경계 스키마(`../*.json`)가 `$ref`로 가리키는 타입 **95개를 타입별 파일**로 나눈 것이다. 각 파일은 그 타입과 그 타입이 (연쇄적으로) 참조하는 타입을 `$defs`에 모두 담아 **혼자 로드할 수 있다**. 경계 스키마 안의 `#/$defs/<이름>`은 이 목록의 같은 이름이다.

| 타입 | 이름 | 직접 참조하는 타입 | 쓰이는 경계 스키마 |
|---|---|---|---|
| [`Action`](Action.json) |  | — | `AnswerJudgeInput`, `DialoguePlannerInput`, `OrchestratorOutput`, `PlannerOutput`, `ResponseGeneratorInput`, `SessionStore`, `UtteranceParserInput` |
| [`AlertKind`](AlertKind.json) |  | — | `OrchestratorOutput`, `PlannerOutput`, `SessionStore`, `StaffConsoleInput` |
| [`AnswerJudgeInput`](AnswerJudgeInput.json) |  | [`Directive`](Directive.json), [`Item`](Item.json), [`ItemCheck`](ItemCheck.json), [`PendingId`](PendingId.json), [`QuestionId`](QuestionId.json), [`SlotRef`](SlotRef.json) | — |
| [`AnswerNormalizerInput`](AnswerNormalizerInput.json) |  | [`AskAction`](AskAction.json), [`CurrentValue`](CurrentValue.json), [`Item`](Item.json), [`PendingId`](PendingId.json), [`QuestionDef`](QuestionDef.json), [`SlotRef`](SlotRef.json), [`Target`](Target.json), [`Value`](Value.json) | — |
| [`AskAction`](AskAction.json) |  | — | `AnswerJudgeInput`, `AnswerNormalizerInput`, `DialoguePlannerInput`, `OrchestratorOutput`, `PlannerOutput`, `ResponseGeneratorInput`, `SessionStore`, `UtteranceParserInput` |
| [`AskDirective`](AskDirective.json) |  | [`AskAction`](AskAction.json), [`PendingId`](PendingId.json), [`SayValue`](SayValue.json), [`Target`](Target.json) | `AnswerJudgeInput`, `DialoguePlannerInput`, `OrchestratorOutput`, `PlannerOutput`, `ResponseGeneratorInput`, `SessionStore`, `UtteranceParserInput` |
| [`AskSubject`](AskSubject.json) |  | [`Target`](Target.json) | `DialoguePlannerInput`, `PlannerOutput`, `SessionStore` |
| [`ChangedSlot`](ChangedSlot.json) |  | [`SlotRef`](SlotRef.json), [`Value`](Value.json) | `DialoguePlannerInput`, `OrchestratorOutput`, `SessionStore`, `StoreResult` |
| [`CurrentValue`](CurrentValue.json) |  | [`Value`](Value.json) | `AnswerNormalizerInput`, `DialoguePlannerInput`, `DispatchInput`, `RecordWriterInput`, `SessionStore` |
| [`Decision`](Decision.json) |  | — | `InterventionDecision`, `OrchestratorInput`, `OrchestratorOutput`, `SessionStore` |
| [`DialoguePlannerInput`](DialoguePlannerInput.json) |  | [`Directive`](Directive.json), [`Judgment`](Judgment.json), [`OpenRequests`](OpenRequests.json), [`PlannerRecord`](PlannerRecord.json), [`QuestionBank`](QuestionBank.json), [`SkipEntry`](SkipEntry.json), [`SlotRecord`](SlotRecord.json), [`SlotRef`](SlotRef.json), [`StoreSummary`](StoreSummary.json), [`TurnKind`](TurnKind.json), [`UtteranceJudgment`](UtteranceJudgment.json) | — |
| [`Directive`](Directive.json) |  | [`Action`](Action.json), [`AskDirective`](AskDirective.json), [`Notice`](Notice.json), [`PendingId`](PendingId.json), [`Reason`](Reason.json), [`SayValue`](SayValue.json), [`SentenceMaterials`](SentenceMaterials.json), [`Target`](Target.json) | `AnswerJudgeInput`, `DialoguePlannerInput`, `OrchestratorOutput`, `PlannerOutput`, `ResponseGeneratorInput`, `SessionStore`, `UtteranceParserInput` |
| [`DispatchInput`](DispatchInput.json) |  | [`PauseEntry`](PauseEntry.json), [`SessionInfo`](SessionInfo.json), [`SessionStatus`](SessionStatus.json), [`SkipEntry`](SkipEntry.json), [`SlotRecord`](SlotRecord.json), [`SlotRef`](SlotRef.json) | — |
| [`DispatchOutput`](DispatchOutput.json) |  | [`DispatchRecord`](DispatchRecord.json) | — |
| [`DispatchRecord`](DispatchRecord.json) |  | — | `DispatchOutput`, `SessionStore` |
| [`FailedStep`](FailedStep.json) |  | — | `OrchestratorOutput`, `SessionStore` |
| [`FillValue`](FillValue.json) |  | — | `DialoguePlannerInput`, `QuestionBank` |
| [`FixedSentence`](FixedSentence.json) |  | [`FixedSentenceKey`](FixedSentenceKey.json) | `DialoguePlannerInput`, `QuestionBank` |
| [`FixedSentenceKey`](FixedSentenceKey.json) |  | — | `AnswerJudgeInput`, `DialoguePlannerInput`, `OrchestratorOutput`, `PlannerOutput`, `QuestionBank`, `ResponseGeneratorInput`, `SessionStore`, `UtteranceParserInput` |
| [`Flow`](Flow.json) |  | — | `OrchestratorOutput`, `PlannerOutput`, `SessionStore` |
| [`FrontendInput`](FrontendInput.json) |  | [`TurnFailureSignal`](TurnFailureSignal.json) | — |
| [`FrontendMessage`](FrontendMessage.json) |  | [`SessionId`](SessionId.json) | `OrchestratorInput` |
| [`GeneratorOutput`](GeneratorOutput.json) |  | — | — |
| [`GuideItem`](GuideItem.json) |  | [`FillValue`](FillValue.json) | `DialoguePlannerInput`, `QuestionBank` |
| [`InputKind`](InputKind.json) |  | — | `OrchestratorOutput`, `SessionStore` |
| [`Intent`](Intent.json) |  | — | `AnswerJudgeInput`, `AnswerNormalizerInput`, `OrchestratorOutput`, `ParserOutput`, `SessionStore` |
| [`InterventionDecision`](InterventionDecision.json) |  | [`Decision`](Decision.json), [`SessionId`](SessionId.json) | `OrchestratorInput` |
| [`InterventionResult`](InterventionResult.json) |  | [`SessionId`](SessionId.json) | `OrchestratorOutput`, `SessionStore`, `StaffConsoleInput` |
| [`Item`](Item.json) |  | [`Intent`](Intent.json), [`ProgressOp`](ProgressOp.json), [`SourceText`](SourceText.json), [`Target`](Target.json) | `AnswerJudgeInput`, `AnswerNormalizerInput`, `OrchestratorOutput`, `ParserOutput`, `SessionStore` |
| [`ItemCheck`](ItemCheck.json) |  | [`Problem`](Problem.json), [`RiskResponse`](RiskResponse.json), [`SlotRef`](SlotRef.json), [`Value`](Value.json) | `AnswerJudgeInput`, `NormalizerOutput`, `OrchestratorOutput`, `SessionStore` |
| [`JudgeOutput`](JudgeOutput.json) |  | [`Judgment`](Judgment.json), [`QuestionId`](QuestionId.json), [`UtteranceJudgment`](UtteranceJudgment.json) | `OrchestratorOutput`, `SessionStore` |
| [`Judgment`](Judgment.json) |  | [`JudgmentStatus`](JudgmentStatus.json), [`PendingId`](PendingId.json), [`Reason`](Reason.json), [`RiskResponse`](RiskResponse.json), [`SlotRef`](SlotRef.json), [`Target`](Target.json), [`Value`](Value.json) | `DialoguePlannerInput`, `JudgeOutput`, `OrchestratorOutput`, `RecordWriterInput`, `SessionStore` |
| [`JudgmentStatus`](JudgmentStatus.json) |  | — | `DialoguePlannerInput`, `JudgeOutput`, `OrchestratorOutput`, `RecordWriterInput`, `SessionStore` |
| [`LogEntry`](LogEntry.json) |  | [`Decision`](Decision.json), [`Directive`](Directive.json), [`FailedStep`](FailedStep.json), [`Flow`](Flow.json), [`InputKind`](InputKind.json), [`InterventionResult`](InterventionResult.json), [`JudgeOutput`](JudgeOutput.json), [`NormalizerOutput`](NormalizerOutput.json), [`ParserOutput`](ParserOutput.json), [`ProgressRecordUpdate`](ProgressRecordUpdate.json), [`StaffAlert`](StaffAlert.json), [`StoreResult`](StoreResult.json), [`TurnFailureSignal`](TurnFailureSignal.json), [`TurnKind`](TurnKind.json) | `OrchestratorOutput`, `SessionStore` |
| [`NormalizerOutput`](NormalizerOutput.json) |  | [`ItemCheck`](ItemCheck.json), [`SlotRef`](SlotRef.json) | `OrchestratorOutput`, `SessionStore` |
| [`Notice`](Notice.json) |  | [`NoticeKind`](NoticeKind.json), [`QuestionId`](QuestionId.json), [`SlotRef`](SlotRef.json), [`Value`](Value.json) | `AnswerJudgeInput`, `DialoguePlannerInput`, `OrchestratorOutput`, `PlannerOutput`, `ResponseGeneratorInput`, `SessionStore`, `UtteranceParserInput` |
| [`NoticeKind`](NoticeKind.json) |  | — | `AnswerJudgeInput`, `DialoguePlannerInput`, `OrchestratorOutput`, `PlannerOutput`, `ResponseGeneratorInput`, `SessionStore`, `UtteranceParserInput` |
| [`OpenRequests`](OpenRequests.json) |  | [`Target`](Target.json) | `DialoguePlannerInput`, `OrchestratorOutput`, `PlannerOutput`, `SessionStore` |
| [`OrchestratorInput`](OrchestratorInput.json) |  | [`FrontendMessage`](FrontendMessage.json), [`InterventionDecision`](InterventionDecision.json), [`SessionStatus`](SessionStatus.json) | — |
| [`OrchestratorOutput`](OrchestratorOutput.json) |  | [`InterventionResult`](InterventionResult.json), [`LogEntry`](LogEntry.json), [`SessionInfo`](SessionInfo.json), [`TurnFailureSignal`](TurnFailureSignal.json), [`TurnKind`](TurnKind.json) | — |
| [`ParserOutput`](ParserOutput.json) |  | [`Item`](Item.json) | `OrchestratorOutput`, `SessionStore` |
| [`PauseEntry`](PauseEntry.json) |  | [`PauseKind`](PauseKind.json), [`PauseReason`](PauseReason.json) | `DispatchInput`, `OrchestratorOutput`, `PlannerOutput`, `SessionStore` |
| [`PauseKind`](PauseKind.json) |  | — | `DispatchInput`, `OrchestratorOutput`, `PlannerOutput`, `SessionStore` |
| [`PauseReason`](PauseReason.json) |  | [`SlotRef`](SlotRef.json), [`SourceText`](SourceText.json) | `DispatchInput`, `OrchestratorOutput`, `PlannerOutput`, `SessionStore` |
| [`PendingId`](PendingId.json) |  | — | `AnswerJudgeInput`, `AnswerNormalizerInput`, `DialoguePlannerInput`, `DispatchInput`, `JudgeOutput`, `OrchestratorOutput`, `PlannerOutput`, `RecordWriterInput`, `ResponseGeneratorInput`, `SessionStore`, `StoreResult`, `UtteranceParserInput` |
| [`PendingRecord`](PendingRecord.json) |  | [`PendingId`](PendingId.json), [`RiskResponse`](RiskResponse.json), [`Value`](Value.json) | `DialoguePlannerInput`, `DispatchInput`, `RecordWriterInput`, `SessionStore` |
| [`PlannerOutput`](PlannerOutput.json) |  | [`Directive`](Directive.json), [`Flow`](Flow.json), [`PlannerRecord`](PlannerRecord.json), [`ProgressRecordUpdate`](ProgressRecordUpdate.json), [`StaffAlert`](StaffAlert.json) | — |
| [`PlannerRecord`](PlannerRecord.json) |  | [`AskSubject`](AskSubject.json), [`QuestionId`](QuestionId.json), [`SlotRef`](SlotRef.json) | `DialoguePlannerInput`, `PlannerOutput`, `SessionStore` |
| [`Policy`](Policy.json) |  | — | `AnswerNormalizerInput`, `DialoguePlannerInput`, `QuestionBank`, `UtteranceParserInput` |
| [`Prerequisite`](Prerequisite.json) |  | [`SlotRef`](SlotRef.json) | `AnswerNormalizerInput`, `DialoguePlannerInput`, `QuestionBank`, `UtteranceParserInput` |
| [`Problem`](Problem.json) |  | — | `AnswerJudgeInput`, `NormalizerOutput`, `OrchestratorOutput`, `SessionStore` |
| [`ProgressOp`](ProgressOp.json) |  | — | `AnswerJudgeInput`, `AnswerNormalizerInput`, `OrchestratorOutput`, `ParserOutput`, `SessionStore` |
| [`ProgressRecord`](ProgressRecord.json) |  | [`Directive`](Directive.json), [`OpenRequests`](OpenRequests.json), [`PauseEntry`](PauseEntry.json), [`SessionStatus`](SessionStatus.json), [`SkipEntry`](SkipEntry.json), [`SlotRef`](SlotRef.json) | `SessionStore` |
| [`ProgressRecordUpdate`](ProgressRecordUpdate.json) |  | [`Directive`](Directive.json), [`OpenRequests`](OpenRequests.json), [`PauseEntry`](PauseEntry.json), [`QuestionId`](QuestionId.json), [`SessionStatus`](SessionStatus.json), [`SkipEntry`](SkipEntry.json), [`SlotRef`](SlotRef.json) | `OrchestratorOutput`, `PlannerOutput`, `SessionStore` |
| [`QuestionBank`](QuestionBank.json) |  | [`QuestionDef`](QuestionDef.json), [`SessionSettings`](SessionSettings.json) | `DialoguePlannerInput` |
| [`QuestionDef`](QuestionDef.json) |  | [`Policy`](Policy.json), [`Prerequisite`](Prerequisite.json), [`QuestionGuideSentence`](QuestionGuideSentence.json), [`QuestionId`](QuestionId.json), [`SlotDef`](SlotDef.json) | `AnswerNormalizerInput`, `DialoguePlannerInput`, `QuestionBank`, `UtteranceParserInput` |
| [`QuestionGuideSentence`](QuestionGuideSentence.json) |  | — | `AnswerNormalizerInput`, `DialoguePlannerInput`, `QuestionBank`, `UtteranceParserInput` |
| [`QuestionId`](QuestionId.json) |  | — | `AnswerJudgeInput`, `AnswerNormalizerInput`, `DialoguePlannerInput`, `DispatchInput`, `JudgeOutput`, `NormalizerOutput`, `OrchestratorOutput`, `ParserOutput`, `PlannerOutput`, `QuestionBank`, `RecordWriterInput`, `ResponseGeneratorInput`, `SessionStore`, `StaffConsoleInput`, `StoreResult`, `UtteranceParserInput` |
| [`Reason`](Reason.json) |  | — | `AnswerJudgeInput`, `DialoguePlannerInput`, `JudgeOutput`, `OrchestratorOutput`, `PlannerOutput`, `RecordWriterInput`, `ResponseGeneratorInput`, `SessionStore`, `UtteranceParserInput` |
| [`RecordWriterInput`](RecordWriterInput.json) |  | [`CurrentValue`](CurrentValue.json), [`Judgment`](Judgment.json), [`PendingRecord`](PendingRecord.json), [`QuestionId`](QuestionId.json), [`SlotRef`](SlotRef.json) | — |
| [`Request`](Request.json) |  | [`QuestionId`](QuestionId.json), [`RequestKind`](RequestKind.json), [`SourceText`](SourceText.json) | `DialoguePlannerInput`, `JudgeOutput`, `OrchestratorOutput`, `SessionStore` |
| [`RequestKind`](RequestKind.json) |  | — | `DialoguePlannerInput`, `JudgeOutput`, `OrchestratorOutput`, `SessionStore` |
| [`ResponseGeneratorInput`](ResponseGeneratorInput.json) |  | [`Directive`](Directive.json) | — |
| [`RiskResponse`](RiskResponse.json) |  | — | `AnswerJudgeInput`, `AnswerNormalizerInput`, `DialoguePlannerInput`, `DispatchInput`, `JudgeOutput`, `NormalizerOutput`, `OrchestratorOutput`, `QuestionBank`, `RecordWriterInput`, `SessionStore`, `StoreResult`, `UtteranceParserInput` |
| [`RiskRule`](RiskRule.json) |  | [`RiskResponse`](RiskResponse.json), [`Value`](Value.json) | `AnswerNormalizerInput`, `DialoguePlannerInput`, `QuestionBank`, `UtteranceParserInput` |
| [`SayValue`](SayValue.json) |  | [`SlotRef`](SlotRef.json), [`Value`](Value.json) | `AnswerJudgeInput`, `DialoguePlannerInput`, `OrchestratorOutput`, `PlannerOutput`, `ResponseGeneratorInput`, `SessionStore`, `UtteranceParserInput` |
| [`SentenceMaterials`](SentenceMaterials.json) |  | [`FixedSentenceKey`](FixedSentenceKey.json), [`QuestionId`](QuestionId.json), [`SlotRef`](SlotRef.json) | `AnswerJudgeInput`, `DialoguePlannerInput`, `OrchestratorOutput`, `PlannerOutput`, `ResponseGeneratorInput`, `SessionStore`, `UtteranceParserInput` |
| [`SessionId`](SessionId.json) |  | — | `DispatchInput`, `FrontendInput`, `FrontendMessage`, `InterventionDecision`, `OrchestratorInput`, `OrchestratorOutput`, `SessionStore`, `StaffConsoleInput` |
| [`SessionInfo`](SessionInfo.json) |  | [`SessionId`](SessionId.json) | `DispatchInput`, `OrchestratorOutput`, `SessionStore` |
| [`SessionSettings`](SessionSettings.json) |  | [`FixedSentence`](FixedSentence.json), [`GuideItem`](GuideItem.json) | `DialoguePlannerInput`, `QuestionBank` |
| [`SessionStatus`](SessionStatus.json) |  | — | `DispatchInput`, `OrchestratorInput`, `OrchestratorOutput`, `PlannerOutput`, `SessionStore` |
| [`SessionStore`](SessionStore.json) |  | [`DispatchRecord`](DispatchRecord.json), [`LogEntry`](LogEntry.json), [`PlannerRecord`](PlannerRecord.json), [`ProgressRecord`](ProgressRecord.json), [`SessionInfo`](SessionInfo.json), [`SlotRecord`](SlotRecord.json) | — |
| [`SkipEntry`](SkipEntry.json) |  | [`QuestionId`](QuestionId.json), [`SkipReason`](SkipReason.json) | `DialoguePlannerInput`, `DispatchInput`, `OrchestratorOutput`, `PlannerOutput`, `SessionStore` |
| [`SkipReason`](SkipReason.json) |  | — | `DialoguePlannerInput`, `DispatchInput`, `OrchestratorOutput`, `PlannerOutput`, `SessionStore` |
| [`SlotDef`](SlotDef.json) |  | [`RiskRule`](RiskRule.json), [`UnitDef`](UnitDef.json) | `AnswerNormalizerInput`, `DialoguePlannerInput`, `QuestionBank`, `UtteranceParserInput` |
| [`SlotRecord`](SlotRecord.json) |  | [`CurrentValue`](CurrentValue.json), [`PendingRecord`](PendingRecord.json), [`RiskResponse`](RiskResponse.json), [`SlotRef`](SlotRef.json), [`Value`](Value.json) | `DialoguePlannerInput`, `DispatchInput`, `SessionStore` |
| [`SlotRef`](SlotRef.json) |  | [`QuestionId`](QuestionId.json) | `AnswerJudgeInput`, `AnswerNormalizerInput`, `DialoguePlannerInput`, `DispatchInput`, `JudgeOutput`, `NormalizerOutput`, `OrchestratorOutput`, `ParserOutput`, `PlannerOutput`, `QuestionBank`, `RecordWriterInput`, `ResponseGeneratorInput`, `SessionStore`, `StaffConsoleInput`, `StoreResult`, `UtteranceParserInput` |
| [`SourceText`](SourceText.json) |  | — | `AnswerJudgeInput`, `AnswerNormalizerInput`, `DialoguePlannerInput`, `DispatchInput`, `JudgeOutput`, `OrchestratorOutput`, `ParserOutput`, `PlannerOutput`, `SessionStore`, `StaffConsoleInput` |
| [`StaffAlert`](StaffAlert.json) |  | [`AlertKind`](AlertKind.json), [`StaffAlertReason`](StaffAlertReason.json) | `OrchestratorOutput`, `PlannerOutput`, `SessionStore`, `StaffConsoleInput` |
| [`StaffAlertReason`](StaffAlertReason.json) |  | [`SlotRef`](SlotRef.json), [`SourceText`](SourceText.json), [`Value`](Value.json) | `OrchestratorOutput`, `PlannerOutput`, `SessionStore`, `StaffConsoleInput` |
| [`StaffConsoleInput`](StaffConsoleInput.json) |  | [`InterventionResult`](InterventionResult.json), [`SessionId`](SessionId.json), [`StaffAlert`](StaffAlert.json), [`TurnFailureSignal`](TurnFailureSignal.json) | — |
| [`StoreAction`](StoreAction.json) |  | — | `OrchestratorOutput`, `SessionStore`, `StoreResult` |
| [`StoreDecision`](StoreDecision.json) |  | [`PendingId`](PendingId.json), [`RiskResponse`](RiskResponse.json), [`SlotRef`](SlotRef.json), [`StoreAction`](StoreAction.json), [`Value`](Value.json) | `OrchestratorOutput`, `SessionStore`, `StoreResult` |
| [`StoreResult`](StoreResult.json) |  | [`StoreDecision`](StoreDecision.json), [`StoreSummary`](StoreSummary.json) | `OrchestratorOutput`, `SessionStore` |
| [`StoreSummary`](StoreSummary.json) |  | [`ChangedSlot`](ChangedSlot.json), [`QuestionId`](QuestionId.json), [`SlotRef`](SlotRef.json) | `DialoguePlannerInput`, `OrchestratorOutput`, `SessionStore`, `StoreResult` |
| [`Target`](Target.json) |  | [`SlotRef`](SlotRef.json), [`WholeQuestion`](WholeQuestion.json) | `AnswerJudgeInput`, `AnswerNormalizerInput`, `DialoguePlannerInput`, `JudgeOutput`, `OrchestratorOutput`, `ParserOutput`, `PlannerOutput`, `RecordWriterInput`, `ResponseGeneratorInput`, `SessionStore`, `UtteranceParserInput` |
| [`TurnFailureSignal`](TurnFailureSignal.json) |  | [`SessionId`](SessionId.json) | `FrontendInput`, `OrchestratorOutput`, `SessionStore`, `StaffConsoleInput` |
| [`TurnKind`](TurnKind.json) |  | — | `DialoguePlannerInput`, `OrchestratorOutput`, `SessionStore` |
| [`UnitDef`](UnitDef.json) |  | — | `AnswerNormalizerInput`, `DialoguePlannerInput`, `QuestionBank`, `UtteranceParserInput` |
| [`UtteranceJudgment`](UtteranceJudgment.json) |  | [`Request`](Request.json), [`SourceText`](SourceText.json), [`UtteranceResult`](UtteranceResult.json), [`ValuelessCorrection`](ValuelessCorrection.json) | `DialoguePlannerInput`, `JudgeOutput`, `OrchestratorOutput`, `SessionStore` |
| [`UtteranceParserInput`](UtteranceParserInput.json) |  | [`Directive`](Directive.json), [`QuestionDef`](QuestionDef.json), [`QuestionId`](QuestionId.json), [`SlotRef`](SlotRef.json), [`Value`](Value.json) | — |
| [`UtteranceResult`](UtteranceResult.json) |  | — | `DialoguePlannerInput`, `JudgeOutput`, `OrchestratorOutput`, `SessionStore` |
| [`Value`](Value.json) |  | — | `AnswerJudgeInput`, `AnswerNormalizerInput`, `DialoguePlannerInput`, `DispatchInput`, `JudgeOutput`, `NormalizerOutput`, `OrchestratorOutput`, `PlannerOutput`, `QuestionBank`, `RecordWriterInput`, `ResponseGeneratorInput`, `SessionStore`, `StaffConsoleInput`, `StoreResult`, `UtteranceParserInput` |
| [`ValuelessCorrection`](ValuelessCorrection.json) |  | [`Target`](Target.json) | `DialoguePlannerInput`, `JudgeOutput`, `OrchestratorOutput`, `SessionStore` |
| [`WholeQuestion`](WholeQuestion.json) |  | [`QuestionId`](QuestionId.json) | `AnswerJudgeInput`, `AnswerNormalizerInput`, `DialoguePlannerInput`, `JudgeOutput`, `OrchestratorOutput`, `ParserOutput`, `PlannerOutput`, `RecordWriterInput`, `ResponseGeneratorInput`, `SessionStore`, `UtteranceParserInput` |
