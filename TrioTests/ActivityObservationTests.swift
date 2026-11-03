import Foundation
import Testing
@testable import Trio

@Suite("Activity observation history") struct ActivityObservationTests {
    private let now = Date(timeIntervalSince1970: 1_800_000_000)

    private func sample(
        id: String = "heart-rate", secondsAgo: TimeInterval = 60,
        value: Double = 100, source: String = "Apple Watch"
    ) -> ActivityObservation {
        let date = now.addingTimeInterval(-secondsAgo)
        return ActivityObservation(
            id: id, kind: .heartRate, startDate: date, endDate: date,
            receivedAt: now, value: value, source: source, detail: ""
        )
    }

    @Test("Repeated Health samples retain their first arrival time") func deduplication() {
        var history = ActivityObservationHistory()
        let original = sample()
        history.merge([original], now: now)
        let redelivered = ActivityObservation(
            id: original.id, kind: original.kind, startDate: original.startDate, endDate: original.endDate,
            receivedAt: now.addingTimeInterval(300), value: original.value, source: original.source, detail: ""
        )
        history.merge([redelivered], now: now.addingTimeInterval(300))
        #expect(history.observations == [original])
    }

    @Test("Late samples are ordered by measurement time without losing arrival time") func lateArrival() {
        var history = ActivityObservationHistory()
        let latest = sample(id: "latest", secondsAgo: 10)
        let delayed = sample(id: "delayed", secondsAgo: 600)
        history.merge([latest, delayed], now: now)
        #expect(history.observations.map(\.id) == ["delayed", "latest"])
        #expect(history.observations.first?.receivedAt == now)
    }

    @Test("Health deletions remove matching stored samples") func deletion() {
        var history = ActivityObservationHistory()
        history.merge([sample()], now: now)
        history.merge([], deleting: ["heart-rate"], now: now)
        #expect(history.observations.isEmpty)
    }

    @Test("Retention excludes old and future samples and invalid values") func retentionAndValidation() {
        var history = ActivityObservationHistory()
        let invalidInterval = ActivityObservation(
            id: "invalid", kind: .phoneSteps, startDate: now, endDate: now.addingTimeInterval(-10),
            receivedAt: now, value: 5, source: "iPhone", detail: ""
        )
        history.merge([
            sample(id: "old", secondsAgo: ActivityObservationHistory.retention + 1),
            sample(id: "future", secondsAgo: -60), sample(id: "nan", value: .nan),
            invalidInterval, sample(id: "valid")
        ], now: now)
        #expect(history.observations.map(\.id) == ["valid"])
        history.merge([], now: now.addingTimeInterval(ActivityObservationHistory.retention))
        #expect(history.observations.isEmpty)
    }

    @Test("The count limit retains the most recent measurements") func countLimit() {
        var history = ActivityObservationHistory()
        let count = ActivityObservationHistory.maximumCount + 10
        history.merge((0 ..< count).map { sample(id: String($0), secondsAgo: Double($0)) }, now: now)
        #expect(history.observations.count == ActivityObservationHistory.maximumCount)
        #expect(history.observations.last?.id == "0")
        #expect(history.observations.contains(where: { $0.id == String(count - 1) }) == false)
    }

    @Test("Saved histories preserve timestamps and sources") func persistenceRoundTrip() throws {
        var history = ActivityObservationHistory()
        history.merge([sample()], now: now)
        let restored = try JSONDecoder().decode(ActivityObservationHistory.self, from: JSONEncoder().encode(history))
        #expect(restored.observations == history.observations)
    }

    @Test("Workout automation requires separate opt-in and starts with no selected preset") func workoutDefaults() throws {
        let configuration = WorkoutPresetConfiguration()
        #expect(configuration.isEnabled == false)
        #expect(configuration.presetID.isEmpty)
        let restored = try JSONDecoder().decode(
            WorkoutPresetConfiguration.self, from: JSONEncoder().encode(configuration)
        )
        #expect(restored == configuration)
    }

    @Test("CSV quotes commas, newlines and embedded quotes") func csvEscaping() {
        var history = ActivityObservationHistory()
        history.merge([sample(source: "Watch, \"Alice\"\nSeries")], now: now)
        #expect(history.csv.hasPrefix("id,type,start,end,received,value,source,detail\n"))
        #expect(history.csv.contains("\"Watch, \"\"Alice\"\"\nSeries\""))
        #expect(history.csv.contains("\"100.0\""))
    }
}
