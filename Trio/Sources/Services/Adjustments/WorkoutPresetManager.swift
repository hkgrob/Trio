import Combine
import Foundation
import Swinject
import UserNotifications

/// Explicit workout events only. Passive observation never calls this service.
final class WorkoutPresetManager: ObservableObject {
    @Published private(set) var configuration: WorkoutPresetConfiguration
    @Published private(set) var lastResult: String
    private let resolver: Resolver
    private let defaults = UserDefaults.standard
    private static let configurationKey = "WorkoutPreset.configuration"
    private static let resultKey = "WorkoutPreset.lastResult"

    init(resolver: Resolver) {
        self.resolver = resolver
        configuration = defaults.data(forKey: Self.configurationKey)
            .flatMap { try? JSONDecoder().decode(WorkoutPresetConfiguration.self, from: $0) }
            ?? WorkoutPresetConfiguration()
        lastResult = defaults.string(forKey: Self.resultKey) ?? ""
    }

    func select(kind: ActivityPresetKind, id: String) {
        configuration = WorkoutPresetConfiguration(isEnabled: false, kind: kind, presetID: id)
        save()
    }

    func setEnabled(_ enabled: Bool) {
        configuration.isEnabled = enabled && !configuration.presetID.isEmpty
        save()
        if configuration.isEnabled {
            UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound, .badge]) { _, _ in }
        }
    }

    private func save() {
        defaults.set(try? JSONEncoder().encode(configuration), forKey: Self.configurationKey)
    }

    @MainActor func activateFromWorkout() async -> String {
        guard configuration.isEnabled, !configuration.presetID.isEmpty else {
            return String(localized: "Workout preset activation is disabled. Enable it and select a preset in Trio’s Activity observations settings.")
        }
        let result: String
        do {
            let outcome = try await resolver.resolve(AdjustmentManager.self)!.activateActivityPreset(
                .presetID(configuration.presetID), kind: configuration.kind
            )
            let name = outcome.started?.name ?? String(localized: "Activity preset")
            if let started = outcome.started, started.indefinite {
                result = String(localized: "Workout started. ‘\(name)’ activated with its saved indefinite duration.")
            } else {
                let minutes = outcome.started?.duration.map { NSDecimalNumber(decimal: $0).stringValue } ?? "?"
                result = String(localized: "Workout started. ‘\(name)’ activated for \(minutes) minutes.")
            }
        } catch {
            result = String(localized: "Workout preset was not activated: \(error.localizedDescription)")
        }
        lastResult = Date().formatted(date: .abbreviated, time: .standard) + " — " + result
        defaults.set(lastResult, forKey: Self.resultKey)

        let content = UNMutableNotificationContent()
        content.title = String(localized: "Trio workout preset")
        content.body = result
        content.sound = .default
        do {
            try await UNUserNotificationCenter.current().add(UNNotificationRequest(
                identifier: "Trio.workoutPreset.\(UUID().uuidString)", content: content, trigger: nil
            ))
        } catch {
            lastResult += " " + String(localized: "Notification could not be delivered: \(error.localizedDescription)")
            defaults.set(lastResult, forKey: Self.resultKey)
        }
        return result
    }
}
