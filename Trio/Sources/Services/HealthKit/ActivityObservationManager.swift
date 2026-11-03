import Combine
import CoreMotion
import Foundation
import HealthKit
import Swinject
import UIKit

/// Passive, local-only collection. Intentionally has no APS, pump or adjustment dependency.
/// Mutable state is confined to the main queue; HealthKit and motion callbacks hop to it.
final class ActivityObservationManager: ObservableObject {
    struct Update {
        let observations: [ActivityObservation]
        let deletedIDs: Set<String>
    }

    let observationUpdates = PassthroughSubject<Update, Never>()
    @Published private(set) var isEnabled: Bool
    @Published private(set) var history = ActivityObservationHistory()
    @Published private(set) var healthStatus = ""
    @Published private(set) var motionStatus = ""
    @Published private(set) var storageError = ""
    @Published private(set) var isRequestingPermission = false

    private let healthStore: HKHealthStore
    private let motion = CMMotionActivityManager()
    private let pedometer = CMPedometer()
    private let defaults: UserDefaults
    private let historyURL: URL
    private let persistenceQueue = DispatchQueue(label: "ActivityObservation.persistence", qos: .utility)
    private var observer: HKObserverQuery?
    private var activeQuery: HKQuery?
    private var queryCompletions: [() -> Void] = []
    private var needsAnotherQuery = false
    private var anchor: HKQueryAnchor?
    private var generation = UUID()
    private var subscriptions = Set<AnyCancellable>()
    private var lastStepEnd: Date?
    private var lastStepQueryEnd: Date?
    private var collectionStart: Date

    private static let enabledKey = "ActivityObservation.enabled"
    private static let startKey = "ActivityObservation.start"
    private static let anchorKey = "ActivityObservation.heartRateAnchor"

    init(resolver: Resolver) {
        healthStore = resolver.resolve(HKHealthStore.self)!
        defaults = .standard
        isEnabled = defaults.bool(forKey: Self.enabledKey)
        collectionStart = defaults.object(forKey: Self.startKey) as? Date ?? Date()
        historyURL = URL.applicationSupportDirectory.appendingPathComponent("activity-observations.json")
        var historyWasPruned = false
        do {
            if FileManager.default.fileExists(atPath: historyURL.path) {
                history = try JSONDecoder().decode(ActivityObservationHistory.self, from: Data(contentsOf: historyURL))
                let previousCount = history.observations.count
                history.merge([])
                historyWasPruned = previousCount != history.observations.count
            }
        } catch {
            storageError = String(localized: "Could not read the activity history. Clear it before collecting more data.")
        }
        if let data = defaults.data(forKey: Self.anchorKey) {
            anchor = try? NSKeyedUnarchiver.unarchivedObject(ofClass: HKQueryAnchor.self, from: data)
        }

        Foundation.NotificationCenter.default.publisher(for: UIApplication.didBecomeActiveNotification)
            .receive(on: DispatchQueue.main)
            .sink { [weak self] _ in self?.refresh() }
            .store(in: &subscriptions)
        // An existing execution opportunity, not a request for extra background runtime.
        resolver.resolve(GlucoseStorage.self)!.updatePublisher
            .receive(on: DispatchQueue.main)
            .sink { [weak self] _ in self?.refresh() }
            .store(in: &subscriptions)
        Timer.publish(every: 60, on: .main, in: .common).autoconnect()
            .sink { [weak self] _ in self?.readStepInterval() }
            .store(in: &subscriptions)

        if historyWasPruned { persist() }
        if isEnabled, storageError.isEmpty { start() }
    }

    func setEnabled(_ enabled: Bool) {
        if !enabled {
            isEnabled = false
            isRequestingPermission = false
            defaults.set(false, forKey: Self.enabledKey)
            stop()
            return
        }
        guard !isRequestingPermission, !isEnabled else { return }
        guard storageError.isEmpty, let heartRate = HKQuantityType.quantityType(forIdentifier: .heartRate),
              HKHealthStore.isHealthDataAvailable()
        else {
            healthStatus = String(localized: "Health data is unavailable. Activity collection was not enabled.")
            return
        }
        isRequestingPermission = true
        let requestGeneration = generation
        healthStore.requestAuthorization(toShare: [], read: [heartRate]) { [weak self] success, error in
            DispatchQueue.main.async {
                guard let self, self.generation == requestGeneration else { return }
                self.isRequestingPermission = false
                guard success, error == nil else {
                    self.healthStatus = error?
                        .localizedDescription ?? String(localized: "Health authorization could not be requested.")
                    return
                }
                // HealthKit deliberately does not disclose whether read access was granted.
                self.collectionStart = Date()
                self.defaults.set(self.collectionStart, forKey: Self.startKey)
                self.anchor = nil
                self.defaults.removeObject(forKey: Self.anchorKey)
                self.isEnabled = true
                self.defaults.set(true, forKey: Self.enabledKey)
                self.start()
            }
        }
    }

    func refresh() {
        guard isEnabled, storageError.isEmpty else { return }
        readHeartRate()
        readStepInterval()
    }

    private func start() {
        guard isEnabled, observer == nil,
              let type = HKQuantityType.quantityType(forIdentifier: .heartRate) else { return }
        let currentGeneration = generation
        let query = HKObserverQuery(sampleType: type, predicate: nil) { [weak self] _, completion, error in
            DispatchQueue.main.async {
                guard let self, self.isEnabled, self.generation == currentGeneration else {
                    completion()
                    return
                }
                if let error {
                    self.healthStatus = error.localizedDescription
                    completion()
                } else {
                    self.readHeartRate(completion: completion)
                }
            }
        }
        observer = query
        healthStore.execute(query)
        healthStore.enableBackgroundDelivery(for: type, frequency: .immediate) { [weak self] success, error in
            DispatchQueue.main.async {
                guard let self, self.generation == currentGeneration, self.isEnabled else { return }
                if !success {
                    self.healthStatus = error?
                        .localizedDescription ?? String(localized: "Background Health updates are unavailable.")
                }
            }
        }
        startMotion()
        refresh()
    }

    private func stop() {
        generation = UUID()
        if let observer { healthStore.stop(observer) }
        observer = nil
        // In-flight finite queries finish normally so every HealthKit observer completion is called.
        motion.stopActivityUpdates()
        pedometer.stopUpdates()
        lastStepEnd = nil
        lastStepQueryEnd = nil
        if let type = HKQuantityType.quantityType(forIdentifier: .heartRate) {
            healthStore.disableBackgroundDelivery(for: type) { _, _ in }
        }
    }

    private func readHeartRate(completion: @escaping () -> Void = {}) {
        guard let type = HKQuantityType.quantityType(forIdentifier: .heartRate) else {
            completion()
            return
        }
        queryCompletions.append(completion)
        guard activeQuery == nil else {
            needsAnotherQuery = true
            return
        }
        let currentGeneration = generation
        let startDate = max(collectionStart, Date().addingTimeInterval(-ActivityObservationHistory.retention))
        let predicate = HKQuery.predicateForSamples(withStart: startDate, end: nil, options: .strictStartDate)
        let query = HKAnchoredObjectQuery(type: type, predicate: predicate, anchor: anchor, limit: HKObjectQueryNoLimit) {
            [weak self] _, samples, deleted, nextAnchor, error in
            let receivedAt = Date()
            let readings = (samples as? [HKQuantitySample] ?? []).map { sample in
                ActivityObservation(
                    id: sample.uuid.uuidString, kind: .heartRate, startDate: sample.startDate,
                    endDate: sample.endDate, receivedAt: receivedAt,
                    value: sample.quantity.doubleValue(for: HKUnit.count().unitDivided(by: .minute())),
                    source: sample.sourceRevision.source.name,
                    detail: sample.device?.model ?? "",
                    isWatchHeartRate: sample.metadata?[HKMetadataKeyWasUserEntered] as? Bool != true && (
                        sample.sourceRevision.productType?.hasPrefix("Watch") == true ||
                            sample.device?.model?.localizedCaseInsensitiveContains("watch") == true
                    )
                )
            }
            let deletedIDs = Set((deleted ?? []).map(\.uuid.uuidString))
            DispatchQueue.main.async {
                guard let self else { completion()
                    return }
                guard self.isEnabled, self.generation == currentGeneration else {
                    self.finishQuery()
                    if self.isEnabled { self.refresh() }
                    return
                }
                guard error == nil else {
                    self.healthStatus = error!.localizedDescription
                    self.finishQuery()
                    return
                }
                self.history.merge(readings, deleting: deletedIDs, now: receivedAt)
                self
                    .healthStatus =
                    String(
                        localized: "Reading available Health samples. No samples can mean no read permission or no recent measurements."
                    )
                self.persist { saved in
                    guard saved, self.generation == currentGeneration, self.isEnabled else {
                        self.finishQuery()
                        return
                    }
                    self.anchor = nextAnchor
                    if let nextAnchor,
                       let data = try? NSKeyedArchiver.archivedData(withRootObject: nextAnchor, requiringSecureCoding: true)
                    {
                        self.defaults.set(data, forKey: Self.anchorKey)
                    }
                    self.observationUpdates.send(Update(observations: readings, deletedIDs: deletedIDs))
                    self.finishQuery()
                }
            }
        }
        activeQuery = query
        healthStore.execute(query)
    }

    private func finishQuery() {
        activeQuery = nil
        if needsAnotherQuery, isEnabled, storageError.isEmpty {
            needsAnotherQuery = false
            readHeartRate()
            return
        }
        needsAnotherQuery = false
        let completions = queryCompletions
        queryCompletions = []
        completions.forEach { $0() }
    }

    private func startMotion() {
        let currentGeneration = generation
        if CMMotionActivityManager.isActivityAvailable() {
            motion.startActivityUpdates(to: .main) { [weak self] activity in
                guard let self, self.isEnabled, self.generation == currentGeneration, let activity else { return }
                let labels = [
                    (activity.walking, "walking"), (activity.running, "running"), (activity.cycling, "cycling"),
                    (activity.automotive, "automotive"), (activity.stationary, "stationary"), (activity.unknown, "unknown")
                ].filter { $0.0 }.map(\.1).joined(separator: ", ")
                let confidence: String
                switch activity.confidence {
                case .low: confidence = "low"
                case .medium: confidence = "medium"
                case .high: confidence = "high"
                @unknown default: confidence = "unknown"
                }
                self.motionStatus = String(localized: "iPhone motion updates available.")
                self.record(ActivityObservation(
                    id: UUID().uuidString, kind: .phoneMotion, startDate: activity.startDate,
                    endDate: activity.startDate, receivedAt: Date(), value: nil, source: "iPhone",
                    detail: "\(labels); confidence=\(confidence)"
                ))
            }
        } else {
            motionStatus = String(localized: "Motion activity classification is unavailable on this device.")
        }
        guard CMPedometer.isStepCountingAvailable() else { return }
        let start = Date()
        pedometer.startUpdates(from: start) { [weak self] data, error in
            DispatchQueue.main.async {
                guard let self, self.isEnabled, self.generation == currentGeneration else { return }
                if let error { self.motionStatus = error.localizedDescription
                    return }
                guard let data,
                      data.endDate.timeIntervalSince(self.lastStepEnd ?? start) >= 60 else { return }
                self.lastStepEnd = data.endDate
                // Each observation is cumulative from this session's start, not an additive step delta.
                self.record(ActivityObservation(
                    id: UUID().uuidString, kind: .phoneSteps, startDate: data.startDate, endDate: data.endDate,
                    receivedAt: Date(), value: data.numberOfSteps.doubleValue, source: "iPhone",
                    detail: "cumulative steps since startDate"
                ))
            }
        }
    }

    private func record(_ observation: ActivityObservation) {
        let currentGeneration = generation
        history.merge([observation])
        persist { [weak self] saved in
            guard let self, saved, self.isEnabled, self.generation == currentGeneration else { return }
            self.observationUpdates.send(Update(observations: [observation], deletedIDs: []))
        }
    }

    private func readStepInterval() {
        guard isEnabled, storageError.isEmpty, CMPedometer.isStepCountingAvailable() else { return }
        let end = Date()
        if let lastStepQueryEnd, end.timeIntervalSince(lastStepQueryEnd) < 60 { return }
        lastStepQueryEnd = end
        let start = end.addingTimeInterval(-60)
        let currentGeneration = generation
        // Query actual counts, including zero. The live stream need not emit while stationary.
        pedometer.queryPedometerData(from: start, to: end) { [weak self] data, error in
            DispatchQueue.main.async {
                guard let self, self.isEnabled, self.generation == currentGeneration else { return }
                if let error { self.motionStatus = error.localizedDescription
                    return }
                guard let data else { return }
                self.record(ActivityObservation(
                    id: UUID().uuidString, kind: .phoneStepInterval, startDate: data.startDate,
                    endDate: data.endDate, receivedAt: Date(), value: data.numberOfSteps.doubleValue,
                    source: "iPhone", detail: "steps in measured interval"
                ))
            }
        }
    }

    private func persist(completion: @escaping (Bool) -> Void = { _ in }) {
        let snapshot = history
        let url = historyURL
        persistenceQueue.async {
            do {
                try FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
                try JSONEncoder().encode(snapshot)
                    .write(to: url, options: [.atomic, .completeFileProtectionUntilFirstUserAuthentication])
                DispatchQueue.main.async { completion(true) }
            } catch {
                DispatchQueue.main.async {
                    self.storageError = String(localized: "Could not save activity history: \(error.localizedDescription)")
                    self.setEnabled(false)
                    completion(false)
                }
            }
        }
    }

    func clearHistory() {
        // Disable first so callbacks cannot repopulate cleared records or advance an old anchor.
        setEnabled(false)
        history = ActivityObservationHistory()
        anchor = nil
        defaults.removeObject(forKey: Self.anchorKey)
        storageError = ""
        persist()
    }
}
