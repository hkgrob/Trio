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
    private let expiresAt: Date?

    init(expiresAt: Date? = nil) {
        self.expiresAt = expiresAt
    }

    var isCancelled: Bool {
        !isValid(at: Date())
    }

    func isValid(at now: Date) -> Bool {
        lock.lock()
        defer { lock.unlock() }
        if let expiresAt, now >= expiresAt { cancelled = true }
        return !cancelled
    }

    func cancel() {
        lock.lock()
        defer { lock.unlock() }
        cancelled = true
    }
}

extension Foundation.Notification.Name {
    static let activityAdjustmentRequested = Self("Trio.activityAdjustmentRequested")
}

/// Synchronous on the main actor: invalidate pending automation before a manual mutation starts.
@MainActor func notifyActivityAdjustmentRequested() {
    Foundation.NotificationCenter.default.post(name: .activityAdjustmentRequested, object: nil)
}
