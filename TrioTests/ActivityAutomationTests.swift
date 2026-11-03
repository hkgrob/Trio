import Foundation
import Testing
@testable import Trio

@Suite("Passive activity automation") struct ActivityAutomationTests {
    private let start = Date(timeIntervalSince1970: 1_800_000_000)

    // Synthetic test values, not recommended therapy or exercise settings.
    private var configuration: ActivityAutomationConfiguration {
        var value = ActivityAutomationConfiguration()
        value.isEnabled = true
        value.heartRateBPM = 120
        value.stepsPerMinute = 80
        value.sustainedMinutes = 2
        value.recoveryMinutes = 2
        return value
    }

    private func detector(latched: Bool = false) -> ActivityAutomationDetector {
        ActivityAutomationDetector(configuration: configuration, isLatched: latched, armedAt: start)
    }

    private func watch(_ seconds: Double, bpm: Double = 140, trusted: Bool = true) -> ActivityObservation {
        let date = start.addingTimeInterval(seconds)
        return ActivityObservation(
            id: "hr-\(seconds)-\(bpm)", kind: .heartRate, startDate: date, endDate: date,
            receivedAt: date, value: bpm, source: "Apple Watch", detail: "Watch", isWatchHeartRate: trusted
        )
    }

    private func steps(_ seconds: Double, count: Double, session: Double = 0) -> ActivityObservation {
        ActivityObservation(
            id: "steps-\(seconds)-\(count)", kind: .phoneSteps, startDate: start.addingTimeInterval(session),
            endDate: start.addingTimeInterval(seconds), receivedAt: start.addingTimeInterval(seconds),
            value: count, source: "iPhone", detail: "cumulative"
        )
    }

    private func interval(_ seconds: Double, count: Double) -> ActivityObservation {
        ActivityObservation(
            id: "interval-\(seconds)-\(count)", kind: .phoneStepInterval,
            startDate: start.addingTimeInterval(seconds - 60), endDate: start.addingTimeInterval(seconds),
            receivedAt: start.addingTimeInterval(seconds), value: count, source: "iPhone", detail: "interval"
        )
    }

    private func process(
        _ detector: inout ActivityAutomationDetector,
        _ seconds: Double,
        _ observations: ActivityObservation...
    ) -> Bool {
        detector.process(observations, now: start.addingTimeInterval(seconds))
    }

    @Test("Automation has no preselected activity thresholds and is disabled by default") func defaults() {
        let value = ActivityAutomationConfiguration()
        #expect(value.isEnabled == false)
        #expect(value.heartRateBPM == nil)
        #expect(value.stepsPerMinute == nil)
        #expect(value.sustainedMinutes == nil)
        #expect(value.recoveryMinutes == nil)
        #expect(value.isValid == false)
    }

    @Test("Invalid and non-finite configuration cannot qualify") func invalidConfiguration() {
        for bad in [Double.zero, -1, .nan, .infinity] {
            var value = configuration
            value.heartRateBPM = bad
            #expect(!value.isValid)
            var engine = ActivityAutomationDetector(configuration: value, isLatched: false, armedAt: start)
            #expect(!process(&engine, 0, watch(0)))
            #expect(!process(&engine, 120, watch(120)))
        }
    }

    @Test("Disabled automation never qualifies") func disabled() {
        var value = configuration
        value.isEnabled = false
        var engine = ActivityAutomationDetector(configuration: value, isLatched: false, armedAt: start)
        #expect(!process(&engine, 0, watch(0)))
        #expect(!process(&engine, 120, watch(120)))
        #expect(!engine.isLatched)
    }

    @Test("Watch heart rate alone triggers after sustained fresh measurements") func watchOnly() {
        var engine = detector()
        #expect(!process(&engine, 0, watch(0)))
        #expect(!process(&engine, 60, watch(60)))
        #expect(process(&engine, 120, watch(120)))
        #expect(engine.source == .watch)
        #expect(engine.isLatched)
    }

    @Test("Fresh low Watch heart rate vetoes elevated iPhone movement") func watchVetoesPhone() {
        var engine = detector()
        for seconds in stride(from: 0.0, through: 300, by: 60) {
            #expect(!process(&engine, seconds, watch(seconds, bpm: 90), steps(seconds, count: seconds * 2)))
        }
        #expect(engine.source == .watch)
        #expect(!engine.isLatched)
    }

    @Test("Stationary phone and invalid phone intervals do not interrupt Watch qualification") func phoneCannotVetoWatch() {
        var engine = detector()
        #expect(!process(&engine, 0, watch(0)))
        #expect(!process(&engine, 60, watch(60), steps(60, count: 0)))
        #expect(process(&engine, 120, watch(120), steps(120, count: 0, session: -600)))
    }

    @Test("Phone movement qualifies when Watch data is unavailable") func phoneFallback() {
        var engine = detector()
        #expect(!process(&engine, 60, steps(60, count: 100)))
        #expect(!process(&engine, 120, steps(120, count: 200)))
        #expect(process(&engine, 180, steps(180, count: 300)))
        #expect(engine.source == .phone)
    }

    @Test("Queried step intervals can qualify without a live pedometer stream") func queriedPhoneFallback() {
        var engine = detector()
        #expect(!process(&engine, 60, interval(60, count: 100)))
        #expect(!process(&engine, 120, interval(120, count: 100)))
        #expect(process(&engine, 180, interval(180, count: 100)))
    }

    @Test("Actual zero-step query results can demonstrate recovery") func queriedStationaryRecovery() {
        var engine = detector(latched: true)
        #expect(!process(&engine, 60, interval(60, count: 0)))
        #expect(!process(&engine, 120, interval(120, count: 0)))
        #expect(!process(&engine, 180, interval(180, count: 0)))
        #expect(!engine.isLatched)
    }

    @Test("Cumulative diagnostics cannot override queried interval evidence") func queriedIntervalsTakePrecedence() {
        var engine = detector()
        #expect(!process(&engine, 60, interval(60, count: 100)))
        #expect(!process(&engine, 90, steps(90, count: 900)))
        #expect(!process(&engine, 120, interval(120, count: 0)))
        #expect(!process(&engine, 150, steps(150, count: 1500)))
        #expect(!process(&engine, 180, interval(180, count: 100)))
        #expect(!process(&engine, 240, interval(240, count: 100)))
        #expect(!engine.isLatched)
    }

    @Test("The freshness limit must accommodate the one-minute phone interval") func phoneIntervalCadence() {
        var value = configuration
        value.maximumGapMinutes = 0.5
        #expect(!value.isValid)
    }

    @Test("Switching from Watch to phone starts a new qualification window") func sourceSwitch() {
        var engine = detector()
        #expect(!process(&engine, 0, watch(0)))
        #expect(!process(&engine, 60, watch(60), steps(60, count: 100)))
        #expect(!process(&engine, 120, steps(120, count: 200)))
        // At 181 the last Watch sample is stale. Phone evidence cannot inherit the Watch window.
        #expect(!process(&engine, 181, steps(181, count: 300)))
        #expect(engine.source == .phone)
        #expect(!process(&engine, 241, steps(241, count: 400)))
        #expect(process(&engine, 301, steps(301, count: 500)))
    }

    @Test("A fresh low Watch reading stops phone fallback qualification") func watchReturns() {
        var engine = detector()
        #expect(!process(&engine, 60, steps(60, count: 100)))
        #expect(!process(&engine, 120, steps(120, count: 200)))
        #expect(!process(&engine, 150, watch(150, bpm: 90)))
        #expect(!process(&engine, 180, steps(180, count: 300)))
        #expect(engine.source == .watch)
        #expect(!engine.isLatched)
    }

    @Test("A timer cannot turn one held reading into sustained evidence") func heldReading() {
        var engine = detector()
        #expect(!process(&engine, 0, watch(0)))
        let at60 = engine.evaluate(now: start.addingTimeInterval(60))
        let at120 = engine.evaluate(now: start.addingTimeInterval(120))
        let at180 = engine.evaluate(now: start.addingTimeInterval(180))
        #expect(!at60)
        #expect(!at120)
        #expect(!at180)
        #expect(!engine.isLatched)
    }

    @Test("An execution gap restarts qualification even when the arriving sample is fresh") func executionGap() {
        var engine = detector()
        #expect(!process(&engine, 0, watch(0)))
        #expect(!process(&engine, 60, watch(60)))
        #expect(!process(&engine, 300, watch(300)))
        #expect(!process(&engine, 360, watch(360)))
        #expect(process(&engine, 420, watch(420)))
    }

    @Test("A late batch cannot retroactively qualify exercise") func delayedBatch() {
        var engine = detector()
        #expect(!process(&engine, 600, watch(0), watch(60), watch(120), watch(180)))
        #expect(!process(&engine, 600, watch(600)))
        #expect(!engine.isLatched)
    }

    @Test("Pre-arming Watch context cannot qualify activity and future readings are ignored") func timeBounds() {
        var engine = detector()
        #expect(!process(&engine, 0, watch(-60), watch(600)))
        #expect(!engine.isLatched)
        #expect(!process(&engine, 60, watch(600)))
        #expect(!engine.isLatched)
    }

    @Test("A fresh batch ending below threshold cannot request activation") func batchEndsBelowThreshold() {
        var value = configuration
        value.sustainedMinutes = 3
        var engine = ActivityAutomationDetector(configuration: value, isLatched: false, armedAt: start)
        _ = process(&engine, 0, watch(0))
        _ = process(&engine, 60, watch(60))
        _ = process(&engine, 120, watch(120))
        #expect(!process(&engine, 190, watch(180), watch(190, bpm: 80)))
        #expect(!engine.isLatched)
        #expect(engine.phase == .waitingForActivity)
    }

    @Test("A qualifying batch still triggers when its final Watch evidence remains high") func batchEndsAboveThreshold() {
        var engine = detector()
        _ = process(&engine, 0, watch(0))
        _ = process(&engine, 60, watch(60))
        #expect(process(&engine, 130, watch(120), watch(130)))
    }

    @Test("Fresh Watch context on re-arming vetoes phone fallback without qualifying old activity")
    func seededWatchPrecedence() {
        var value = configuration
        value.maximumGapMinutes = 5
        value.sustainedMinutes = 1
        var engine = ActivityAutomationDetector(
            configuration: value, isLatched: false, armedAt: start, initialWatchReading: watch(-5, bpm: 80)
        )
        #expect(!process(&engine, 60, interval(60, count: 100)))
        #expect(!process(&engine, 120, interval(120, count: 100)))
        #expect(engine.source == .watch)
        #expect(!engine.isLatched)
    }

    @Test("Pre-arming Watch context delivered after arming also vetoes fallback") func lateWatchContext() {
        var value = configuration
        value.maximumGapMinutes = 5
        value.sustainedMinutes = 1
        var engine = ActivityAutomationDetector(configuration: value, isLatched: false, armedAt: start)
        #expect(!process(&engine, 60, interval(60, count: 100)))
        #expect(!process(&engine, 70, watch(-5, bpm: 80)))
        #expect(!process(&engine, 120, interval(120, count: 100)))
        #expect(engine.source == .watch)
    }

    @Test("Seeded high Watch context cannot trigger until new measurements span the duration")
    func highWatchContextIsNotQualification() {
        var engine = ActivityAutomationDetector(
            configuration: configuration, isLatched: false, armedAt: start, initialWatchReading: watch(-5)
        )
        #expect(!process(&engine, 0))
        #expect(!process(&engine, 60, watch(60)))
        #expect(process(&engine, 120, watch(120)))
    }

    @Test("Stale or untrusted Watch context does not veto phone fallback") func invalidSeedContext() {
        for seed in [watch(-600, bpm: 80), watch(-5, bpm: 80, trusted: false)] {
            var engine = ActivityAutomationDetector(
                configuration: configuration, isLatched: false, armedAt: start, initialWatchReading: seed
            )
            #expect(!process(&engine, 60, interval(60, count: 100)))
            #expect(!process(&engine, 120, interval(120, count: 100)))
            #expect(process(&engine, 180, interval(180, count: 100)))
        }
    }

    @Test("Pending activation is revoked by a newer below-threshold Watch reading") func pendingWatchVeto() {
        var engine = detector()
        _ = process(&engine, 0, watch(0))
        _ = process(&engine, 60, watch(60))
        #expect(process(&engine, 120, watch(120)))
        let evidence = engine.activationEvidence(now: start.addingTimeInterval(120))!
        let request = ActivityActivationRequest(expiresAt: evidence.expiresAt)
        _ = process(&engine, 130, watch(130, bpm: 80))
        engine.revalidate(request, expectedSource: .watch, now: start.addingTimeInterval(130))
        #expect(!request.isValid(at: start.addingTimeInterval(130)))
    }

    @Test("Watch returning during a queued phone request requires a new source window") func pendingSourceSwitch() {
        var engine = detector()
        _ = process(&engine, 60, interval(60, count: 100))
        _ = process(&engine, 120, interval(120, count: 100))
        #expect(process(&engine, 180, interval(180, count: 100)))
        let evidence = engine.activationEvidence(now: start.addingTimeInterval(180))!
        let request = ActivityActivationRequest(expiresAt: evidence.expiresAt)
        _ = process(&engine, 190, watch(190))
        engine.revalidate(request, expectedSource: .phone, now: start.addingTimeInterval(190))
        #expect(!request.isValid(at: start.addingTimeInterval(190)))
    }

    @Test("A request expires without a sensor callback and cannot be revived") func requestDeadline() {
        let request = ActivityActivationRequest(expiresAt: start.addingTimeInterval(120))
        #expect(request.isValid(at: start.addingTimeInterval(119)))
        #expect(!request.isValid(at: start.addingTimeInterval(120)))
        #expect(!request.isValid(at: start.addingTimeInterval(60)))
    }

    @Test("Manual or non-Watch heart rate cannot trigger or veto phone fallback") func trustedSources() {
        var engine = detector()
        #expect(!process(&engine, 0, watch(0, trusted: false)))
        #expect(!process(&engine, 60, watch(60, bpm: 90, trusted: false), steps(60, count: 100)))
        #expect(!process(&engine, 120, watch(120, bpm: 90, trusted: false), steps(120, count: 200)))
        #expect(process(&engine, 180, watch(180, bpm: 90, trusted: false), steps(180, count: 300)))
        #expect(engine.source == .phone)
    }

    @Test("Cumulative steps are differenced instead of repeatedly counted") func cumulativeSteps() {
        var engine = detector()
        #expect(!process(&engine, 60, steps(60, count: 100)))
        #expect(!process(&engine, 120, steps(120, count: 100)))
        #expect(!process(&engine, 180, steps(180, count: 100)))
        #expect(!engine.isLatched)
    }

    @Test("Long pedometer intervals and decreasing counters cannot qualify") func invalidStepIntervals() {
        var engine = detector()
        #expect(!process(&engine, 60, steps(60, count: 100)))
        #expect(!process(&engine, 120, steps(120, count: 20)))
        #expect(!process(&engine, 600, steps(600, count: 1000)))
        #expect(!engine.isLatched)
    }

    @Test("Repeated high readings cannot retrigger the same episode") func oneTriggerPerEpisode() {
        var engine = detector()
        _ = process(&engine, 0, watch(0))
        _ = process(&engine, 60, watch(60))
        #expect(process(&engine, 120, watch(120)))
        for seconds in stride(from: 180.0, through: 600, by: 60) {
            #expect(!process(&engine, seconds, watch(seconds)))
        }
        #expect(engine.isLatched)
    }

    @Test("Missing data does not re-arm a latched episode") func unknownIsNotRecovery() {
        var engine = detector(latched: true)
        let triggered = engine.evaluate(now: start.addingTimeInterval(3600))
        #expect(!triggered)
        #expect(engine.isLatched)
    }

    @Test("Fresh sustained recovery allows a subsequent episode") func recovery() {
        var engine = detector(latched: true)
        #expect(!process(&engine, 0, watch(0, bpm: 90)))
        #expect(!process(&engine, 60, watch(60, bpm: 90)))
        #expect(!process(&engine, 120, watch(120, bpm: 90)))
        #expect(!engine.isLatched)
        #expect(!process(&engine, 180, watch(180)))
        #expect(!process(&engine, 240, watch(240)))
        #expect(process(&engine, 300, watch(300)))
    }

    @Test("Phone fallback can demonstrate recovery when Watch data is absent") func phoneRecovery() {
        var engine = detector(latched: true)
        #expect(!process(&engine, 60, steps(60, count: 0)))
        #expect(!process(&engine, 120, steps(120, count: 0)))
        #expect(!process(&engine, 180, steps(180, count: 0)))
        #expect(!engine.isLatched)
    }

    @Test("Changing recovery source cannot inherit elapsed recovery") func recoverySourceSwitch() {
        var engine = detector(latched: true)
        #expect(!process(&engine, 0, watch(0, bpm: 90)))
        #expect(!process(&engine, 60, steps(60, count: 0)))
        #expect(!process(&engine, 120, steps(120, count: 0)))
        #expect(!process(&engine, 180, steps(180, count: 0)))
        #expect(engine.isLatched)
        #expect(!process(&engine, 240, steps(240, count: 0)))
        #expect(!process(&engine, 300, steps(300, count: 0)))
        #expect(!engine.isLatched)
    }

    @Test("Manual adjustment changes suppress an episode until fresh recovery") func manualPriority() {
        var engine = detector()
        _ = process(&engine, 0, watch(0))
        _ = process(&engine, 60, watch(60))
        engine.suppressUntilRecovery()
        #expect(!process(&engine, 120, watch(120)))
        #expect(!process(&engine, 180, watch(180)))
        #expect(engine.isLatched)
    }

    @Test("Restoring the latch after a restart prevents repeated activation") func restartLatch() {
        var engine = ActivityAutomationDetector(configuration: configuration, isLatched: true, armedAt: start)
        #expect(!process(&engine, 0, watch(0)))
        #expect(!process(&engine, 60, watch(60)))
        #expect(!process(&engine, 120, watch(120)))
        #expect(engine.isLatched)
    }

    @Test("A late low reading breaks an apparent sustained high run") func lateLow() {
        var engine = detector()
        _ = process(&engine, 0, watch(0))
        _ = process(&engine, 60, watch(60))
        #expect(!process(&engine, 90, watch(30, bpm: 90)))
        #expect(!process(&engine, 120, watch(120)))
        #expect(!engine.isLatched)
    }

    @Test("Deleting the current heart-rate reading invalidates qualification") func deletion() {
        var engine = detector()
        _ = process(&engine, 0, watch(0))
        _ = process(&engine, 60, watch(60))
        let triggered = engine.process([], deleting: [watch(60).id], now: start.addingTimeInterval(90))
        #expect(!triggered)
        #expect(!process(&engine, 120, watch(120)))
        #expect(!process(&engine, 180, watch(180)))
    }
}
