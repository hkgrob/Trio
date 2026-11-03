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
