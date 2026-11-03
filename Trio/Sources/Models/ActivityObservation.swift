import Foundation

/// Sensor observations. Never passed directly to the dosing algorithm.
struct ActivityObservation: Codable, Identifiable, Equatable {
    enum Kind: String, Codable {
        case heartRate
        case phoneSteps
        case phoneStepInterval
        case phoneMotion
    }

    let id: String
    let kind: Kind
    let startDate: Date
    let endDate: Date
    let receivedAt: Date
    let value: Double?
    let source: String
    let detail: String
    var isWatchHeartRate: Bool? = nil
}

struct ActivityObservationHistory: Codable {
    static let retention: TimeInterval = 7 * 24 * 60 * 60
    static let maximumCount = 20000

    private(set) var observations: [ActivityObservation] = []

    mutating func merge(_ incoming: [ActivityObservation], deleting ids: Set<String> = [], now: Date = Date()) {
        let cutoff = now.addingTimeInterval(-Self.retention)
        var known = Set<String>()
        // Keep the original arrival time when HealthKit delivers a sample again.
        observations = (observations + incoming).filter {
            !ids.contains($0.id) && $0.endDate >= cutoff && $0.endDate <= now &&
                $0.startDate <= $0.endDate && ($0.value?.isFinite ?? true) && known.insert($0.id).inserted
        }.sorted {
            $0.endDate == $1.endDate ? $0.id < $1.id : $0.endDate < $1.endDate
        }
        observations = Array(observations.suffix(Self.maximumCount))
    }

    var csv: String {
        let formatter = ISO8601DateFormatter()
        func escaped(_ value: String) -> String {
            "\"" + value.replacingOccurrences(of: "\"", with: "\"\"") + "\""
        }
        let header = "id,type,start,end,received,value,source,detail"
        let rows = observations.map { observation in
            [
                observation.id, observation.kind.rawValue,
                formatter.string(from: observation.startDate), formatter.string(from: observation.endDate),
                formatter.string(from: observation.receivedAt), observation.value.map { String($0) } ?? "",
                observation.source, observation.detail
            ].map(escaped).joined(separator: ",")
        }
        return ([header] + rows).joined(separator: "\n")
    }
}
