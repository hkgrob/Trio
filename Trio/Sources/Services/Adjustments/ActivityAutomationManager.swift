import Combine
import Foundation
import Swinject
import UserNotifications

/// The only bridge between passive sensor collection and saved-preset activation.
/// State and subscriptions run on the main queue; the adjustment manager owns the transaction.
final class ActivityAutomationManager: ObservableObject {
    @Published private(set) var configuration: ActivityAutomationConfiguration
    @Published private(set) var phase: ActivityAutomationDetector.Phase = .waitingForData
    @Published private(set) var source: ActivityAutomationDetector.Source?
    @Published private(set) var isActivating = false

    private let observations: ActivityObservationManager
    private let presets: WorkoutPresetManager
    private let defaults: UserDefaults
    private var detector: ActivityAutomationDetector
    private var generation = UUID()
    private var activationRequest: ActivityActivationRequest?
    private var activationSource: ActivityAutomationDetector.Source?
    private var subscriptions = Set<AnyCancellable>()
    private static let configurationKey = "ActivityAutomation.configuration"
    private static let latchKey = "ActivityAutomation.episodeLatched"

    init(resolver: Resolver) {
        observations = resolver.resolve(ActivityObservationManager.self)!
        presets = resolver.resolve(WorkoutPresetManager.self)!
        defaults = .standard
        var saved = defaults.data(forKey: Self.configurationKey)
            .flatMap { try? JSONDecoder().decode(ActivityAutomationConfiguration.self, from: $0) }
            ?? ActivityAutomationConfiguration()
        if !saved.isValid || !observations.isEnabled || !observations.storageError.isEmpty || presets.configuration.presetID
            .isEmpty
        {
            saved.isEnabled = false
        }
        configuration = saved
        detector = ActivityAutomationDetector(
            configuration: saved, isLatched: defaults.bool(forKey: Self.latchKey), armedAt: Date(),
            initialWatchReading: observations.history.observations.last { $0.kind == .heartRate && $0.isWatchHeartRate == true }
        )
        saveConfiguration()

        observations.observationUpdates.receive(on: DispatchQueue.main)
            .sink { [weak self] update in self?.process(update) }
            .store(in: &subscriptions)
        observations.$isEnabled.receive(on: DispatchQueue.main)
            .sink { [weak self] enabled in
                guard let self, !enabled, self.configuration.isEnabled else { return }
                self.setEnabled(false)
            }
            .store(in: &subscriptions)
        presets.$configuration
            .removeDuplicates { $0.kind == $1.kind && $0.presetID == $1.presetID }
            .dropFirst()
            .receive(on: DispatchQueue.main)
            .sink { [weak self] _ in self?.setEnabled(false) }
            .store(in: &subscriptions)
        // This event is emitted synchronously on the main actor, before manual commands mutate anything.
        Foundation.NotificationCenter.default.publisher(for: .activityAdjustmentRequested)
            .sink { [weak self] _ in self?.suppressForAdjustment() }
            .store(in: &subscriptions)
        // Successful workout/activity starts also suppress passive reactivation. Manual commands
        // already announced their intent; upload completion and automatic expiry must not re-latch.
        let adjustmentNames: [Foundation.Notification.Name] = [
            .didUpdateOverrideConfiguration, .didUpdateTempTargetConfiguration
        ]
        let adjustmentPublishers = adjustmentNames.map { Foundation.NotificationCenter.default.publisher(for: $0) }
        Publishers.MergeMany(adjustmentPublishers)
            .filter { (notification: Foundation.Notification) -> Bool in
                notification.userInfo?["adjustmentSource"] as? String == AdjustmentSource.activity.rawValue
            }
            .receive(on: DispatchQueue.main)
            .sink { [weak self] _ in
                self?.suppressForAdjustment()
            }
            .store(in: &subscriptions)
        Timer.publish(every: 30, on: .main, in: .common).autoconnect()
            .sink { [weak self] _ in self?.tick() }
            .store(in: &subscriptions)
    }

    var canEnable: Bool {
        configuration.isValid && observations.isEnabled && observations.storageError.isEmpty && !presets.configuration.presetID
            .isEmpty
    }

    func update(_ edit: (inout ActivityAutomationConfiguration) -> Void) {
        var updated = configuration
        edit(&updated)
        updated.isEnabled = false
        configuration = updated
        resetDetector()
        saveConfiguration()
    }

    func setEnabled(_ enabled: Bool) {
        configuration.isEnabled = enabled && canEnable
        resetDetector()
        saveConfiguration()
        if configuration.isEnabled {
            UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound, .badge]) { _, _ in }
        }
    }

    private func resetDetector() {
        activationRequest?.cancel()
        generation = UUID()
        detector = ActivityAutomationDetector(
            configuration: configuration, isLatched: detector.isLatched, armedAt: Date(),
            initialWatchReading: observations.history.observations.last { $0.kind == .heartRate && $0.isWatchHeartRate == true }
        )
        phase = detector.isLatched ? .latched : .waitingForData
        source = nil
    }

    private func suppressForAdjustment() {
        guard configuration.isEnabled else { return }
        activationRequest?.cancel()
        generation = UUID()
        detector.suppressUntilRecovery()
        publishState()
    }

    private func validatePendingRequest(now: Date) {
        guard let request = activationRequest else { return }
        detector.revalidate(request, expectedSource: activationSource, now: now)
    }

    private func saveConfiguration() {
        defaults.set(try? JSONEncoder().encode(configuration), forKey: Self.configurationKey)
    }

    private func publishState() {
        phase = detector.phase
        source = detector.source
        defaults.set(detector.isLatched, forKey: Self.latchKey)
    }

    private func process(_ update: ActivityObservationManager.Update) {
        guard configuration.isEnabled, observations.isEnabled, observations.storageError.isEmpty else { return }
        let now = Date()
        let triggered = detector.process(update.observations, deleting: update.deletedIDs, now: now)
        validatePendingRequest(now: now)
        publishState() // Persist the latch before queuing activation, including across app restarts.
        if triggered { activate() }
    }

    private func tick() {
        guard configuration.isEnabled else { return }
        let now = Date()
        let triggered = detector.evaluate(now: now)
        validatePendingRequest(now: now)
        publishState()
        if triggered { activate() }
    }

    private func activate() {
        guard !isActivating, let evidence = detector.activationEvidence(now: Date()) else { return }
        let requestGeneration = generation
        let request = ActivityActivationRequest(expiresAt: evidence.expiresAt)
        activationRequest = request
        activationSource = evidence.source
        Task { @MainActor [weak self] in
            guard let self, self.generation == requestGeneration, self.configuration.isEnabled,
                  self.observations.isEnabled, self.observations.storageError.isEmpty else { return }
            self.isActivating = true
            _ = await self.presets.activateFromActivity(request: request)
            self.isActivating = false
        }
    }
}
