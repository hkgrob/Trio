import Foundation

struct ActivityAutomationConfiguration: Codable, Equatable {
    var isEnabled = false
    var heartRateBPM: Double?
    var stepsPerMinute: Double?
    var sustainedMinutes: Double?
    var recoveryMinutes: Double?
    /// A data freshness limit, not an exercise or dosing threshold.
    var maximumGapMinutes: Double? = 2

    var isValid: Bool {
        let positive = [heartRateBPM, stepsPerMinute, sustainedMinutes, recoveryMinutes, maximumGapMinutes].allSatisfy {
            guard let value = $0 else { return false }
            return value.isFinite && value > 0 && (value * 60).isFinite
        }
        // The phone's queried step intervals span one minute.
        return positive && (maximumGapMinutes ?? 0) >= 1
    }
}

/// Classifies sensor evidence only; it never calculates insulin or modifies a dosing determination.
struct ActivityAutomationDetector {
    enum Source: Equatable {
        case watch
        case phone
    }

    enum Phase: Equatable {
        case waitingForData
        case waitingForActivity
        case qualifying(TimeInterval)
        case latched
        case recovering(TimeInterval)
    }

    private struct Signal {
        let id: String
        let date: Date
        let value: Double
    }

    struct ActivationEvidence {
        let source: Source
        let expiresAt: Date
    }

    let configuration: ActivityAutomationConfiguration
    private(set) var isLatched: Bool
    private(set) var phase: Phase = .waitingForData
    private(set) var source: Source?
    private let armedAt: Date
    private var heartRate: Signal?
    private var movement: Signal?
    private var previousSteps: ActivityObservation?
    private var hasStepIntervals = false
    private var candidateSince: Date?
    private var recoverySince: Date?
    private var lastEvaluation: Date?

    init(
        configuration: ActivityAutomationConfiguration, isLatched: Bool, armedAt: Date,
        initialWatchReading: ActivityObservation? = nil
    ) {
        self.configuration = configuration
        self.isLatched = isLatched
        self.armedAt = armedAt
        if let initialWatchReading { ingest(initialWatchReading, now: armedAt) }
    }

    mutating func suppressUntilRecovery() {
        isLatched = true
        candidateSince = nil
        recoverySince = nil
        phase = .latched
    }

    /// Replays only newly received observations. Historical batches cannot backdate qualification.
    mutating func process(_ observations: [ActivityObservation], deleting ids: Set<String> = [], now: Date) -> Bool {
        if let heartRate, ids.contains(heartRate.id) { self.heartRate = nil }
        if let movement, ids.contains(movement.id) { self.movement = nil }
        if let previousSteps, ids.contains(previousSteps.id) { self.previousSteps = nil }
        _ = evaluate(now: now, allowActivation: false)
        for observation in observations.sorted(by: { $0.endDate < $1.endDate }) where !ids.contains(observation.id) {
            ingest(observation, now: now)
            _ = evaluate(now: now, allowActivation: false)
        }
        return evaluate(now: now)
    }

    private mutating func ingest(_ observation: ActivityObservation, now: Date) {
        guard configuration.isValid,
              (observation.kind == .heartRate || observation.endDate >= armedAt), observation.endDate <= now,
              observation.startDate <= observation.endDate,
              let value = observation.value, value.isFinite else { return }
        switch observation.kind {
        case .heartRate:
            guard observation.isWatchHeartRate == true, value > 0,
                  now.timeIntervalSince(observation.endDate) <= configuration.maximumGapMinutes! * 60 else { return }
            if let current = heartRate, observation.endDate <= current.date {
                // A late low reading invalidates an in-progress claim of sustained activity.
                if let since = candidateSince, observation.endDate >= since,
                   value < (configuration.heartRateBPM ?? .infinity)
                { candidateSince = nil }
                if let since = recoverySince, observation.endDate >= since,
                   value >= (configuration.heartRateBPM ?? .infinity)
                { recoverySince = nil }
                return
            }
            heartRate = Signal(id: observation.id, date: observation.endDate, value: value)
        case .phoneSteps:
            guard !hasStepIntervals else { return }
            guard value >= 0 else { return }
            if let previousSteps, observation.endDate <= previousSteps.endDate { return }
            let previous = previousSteps
            previousSteps = observation
            let start: Date
            let baseline: Double
            if let previous, previous.startDate == observation.startDate, let count = previous.value {
                start = previous.endDate
                baseline = count
            } else {
                start = observation.startDate
                baseline = 0
            }
            let interval = observation.endDate.timeIntervalSince(start)
            let maximumGap = (configuration.maximumGapMinutes ?? 0) * 60
            guard start >= armedAt, interval > 0, interval <= maximumGap, value >= baseline else {
                movement = nil
                if source == .phone {
                    candidateSince = nil
                    recoverySince = nil
                }
                return
            }
            let rate = (value - baseline) * 60 / interval
            guard rate.isFinite else {
                movement = nil
                if source == .phone { candidateSince = nil
                    recoverySince = nil }
                return
            }
            movement = Signal(id: observation.id, date: observation.endDate, value: rate)
        case .phoneStepInterval:
            guard value >= 0, observation.startDate >= armedAt,
                  observation.endDate > (movement?.date ?? .distantPast) else { return }
            let interval = observation.endDate.timeIntervalSince(observation.startDate)
            guard interval > 0, interval <= (configuration.maximumGapMinutes ?? 0) * 60 else { return }
            let rate = value * 60 / interval
            guard rate.isFinite else { return }
            hasStepIntervals = true
            movement = Signal(id: observation.id, date: observation.endDate, value: rate)
        case .phoneMotion:
            break // Activity classifications are diagnostic; step intervals supply the movement evidence.
        }
    }

    /// Current eligibility is independent of the episode latch, so queued requests can be revoked.
    func activationEvidence(now: Date) -> ActivationEvidence? {
        guard configuration.isEnabled, configuration.isValid else { return nil }
        let maximumGap = configuration.maximumGapMinutes! * 60
        let signal: Signal
        let selectedSource: Source
        let threshold: Double
        if let heartRate, heartRate.date <= now, now.timeIntervalSince(heartRate.date) <= maximumGap {
            signal = heartRate
            selectedSource = .watch
            threshold = configuration.heartRateBPM!
        } else if let movement, movement.date <= now, now.timeIntervalSince(movement.date) <= maximumGap {
            signal = movement
            selectedSource = .phone
            threshold = configuration.stepsPerMinute!
        } else {
            return nil
        }
        guard signal.value >= threshold else { return nil }
        return ActivationEvidence(source: selectedSource, expiresAt: signal.date.addingTimeInterval(maximumGap))
    }

    func revalidate(_ request: ActivityActivationRequest, expectedSource: Source?, now: Date) {
        guard request.isValid(at: now), let evidence = activationEvidence(now: now), evidence.source == expectedSource else {
            request.cancel()
            return
        }
    }

    @discardableResult mutating func evaluate(now: Date, allowActivation: Bool = true) -> Bool {
        guard configuration.isEnabled, configuration.isValid else {
            candidateSince = nil
            recoverySince = nil
            phase = .waitingForData
            return false
        }
        let maximumGap = configuration.maximumGapMinutes! * 60
        if let lastEvaluation, now < lastEvaluation || now.timeIntervalSince(lastEvaluation) > maximumGap {
            candidateSince = nil
            recoverySince = nil
        }
        lastEvaluation = now
        func fresh(_ signal: Signal?) -> Signal? {
            guard let signal, signal.date <= now, now.timeIntervalSince(signal.date) <= maximumGap else { return nil }
            return signal
        }
        let heart = fresh(heartRate)
        let steps = fresh(movement)
        // A fresh Watch sample takes precedence even when the phone reports the opposite.
        let selected: (Source, Signal, Double)?
        if let heart {
            selected = (.watch, heart, configuration.heartRateBPM!)
        } else if let steps {
            selected = (.phone, steps, configuration.stepsPerMinute!)
        } else {
            selected = nil
        }
        guard let (selectedSource, signal, threshold) = selected else {
            source = nil
            candidateSince = nil
            recoverySince = nil
            phase = isLatched ? .latched : .waitingForData
            return false
        }
        if source != selectedSource {
            candidateSince = nil
            recoverySince = nil
            source = selectedSource
        }
        let qualifies = signal.value >= threshold

        if isLatched {
            candidateSince = nil
            guard !qualifies else {
                recoverySince = nil
                phase = .latched
                return false
            }
            if recoverySince == nil { recoverySince = now }
            let elapsed = max(0, signal.date.timeIntervalSince(recoverySince!))
            phase = .recovering(elapsed)
            if elapsed >= configuration.recoveryMinutes! * 60 {
                isLatched = false
                recoverySince = nil
                phase = .waitingForActivity
            }
            return false
        }
        recoverySince = nil
        guard qualifies else {
            candidateSince = nil
            phase = .waitingForActivity
            return false
        }
        if candidateSince == nil { candidateSince = now }
        // Qualification must advance on measurements, not on a timer replaying a held value.
        let evidenceDate = signal.date
        let elapsed = max(0, evidenceDate.timeIntervalSince(candidateSince!))
        phase = .qualifying(elapsed)
        guard allowActivation, elapsed >= configuration.sustainedMinutes! * 60 else { return false }
        suppressUntilRecovery()
        return true
    }
}
