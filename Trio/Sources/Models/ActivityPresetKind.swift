import Foundation

enum ActivityPresetKind: String, Codable, CaseIterable {
    case override
    case tempTarget
}

struct WorkoutPresetConfiguration: Codable, Equatable {
    var isEnabled = false
    var kind: ActivityPresetKind = .override
    var presetID = ""
}

/// Cancels a passive activation that is still waiting for the adjustment transaction to begin.
final class ActivityActivationRequest: @unchecked Sendable {
    private let lock = NSLock()
    private var cancelled = false

    var isCancelled: Bool {
        lock.lock()
        defer { lock.unlock() }
        return cancelled
    }

    func cancel() {
        lock.lock()
        defer { lock.unlock() }
        cancelled = true
    }
}
