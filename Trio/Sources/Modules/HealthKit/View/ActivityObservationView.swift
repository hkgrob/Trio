import SwiftUI
import UniformTypeIdentifiers

struct ActivityObservationView: View {
    @ObservedObject var manager: ActivityObservationManager
    @ObservedObject var workoutManager: WorkoutPresetManager
    @ObservedObject var automationManager: ActivityAutomationManager
    @State private var confirmClear = false

    var body: some View {
        List {
            WorkoutPresetSection(manager: workoutManager)
            Section {
                Toggle("Collect activity observations", isOn: Binding(
                    get: { manager.isEnabled },
                    set: { manager.setEnabled($0) }
                ))
                .disabled(manager.isRequestingPermission || (!manager.storageError.isEmpty && !manager.isEnabled))
                if manager.isRequestingPermission { ProgressView() }
            } footer: {
                Text("Collects heart rate and iPhone movement without starting a workout. Preset activation requires the separate automation opt-in below.")
            }

            ActivityAutomationSection(manager: automationManager, observations: manager)

            Section("Latest heart rate") {
                if let reading = manager.history.observations.last(where: { $0.kind == .heartRate }) {
                    observationRow(reading)
                } else {
                    Text("No heart-rate samples received.").foregroundStyle(.secondary)
                }
                Text("Health samples may come from Apple Watch or another authorized source. Measurements and phone synchronization can be delayed; this is not a guaranteed live feed.")
                    .font(.footnote).foregroundStyle(.secondary)
                if !manager.healthStatus.isEmpty { Text(manager.healthStatus).font(.footnote) }
            }

            Section("iPhone movement") {
                if let reading = manager.history.observations.last(where: { $0.kind == .phoneMotion }) {
                    observationRow(reading)
                }
                if let reading = manager.history.observations.last(where: { $0.kind == .phoneStepInterval || $0.kind == .phoneSteps }) {
                    observationRow(reading)
                }
                if !manager.motionStatus.isEmpty { Text(manager.motionStatus).font(.footnote) }
                Text("The phone must be carried for its movement to represent your activity. Motion callbacks pause while Trio is suspended. Live step readings are cumulative; queried interval readings cover their recorded start and end times. Do not add cumulative readings together.")
                    .font(.footnote).foregroundStyle(.secondary)
            }

            Section("Activity history") {
                Text("\(manager.history.observations.count) observations stored")
                ShareLink(
                    item: ActivityObservationExport(history: manager.history),
                    preview: SharePreview("Trio activity observations")
                ) {
                    Label("Export observations (CSV)", systemImage: "square.and.arrow.up")
                }
                .disabled(manager.history.observations.isEmpty)
                Button("Clear history and stop collection", role: .destructive) { confirmClear = true }
                Text("Stored locally: up to 20,000 readings from the past seven days. Export includes measurement time, arrival time and source. Activity observations are not uploaded to Nightscout or sent to LoopFollow.")
                    .font(.footnote).foregroundStyle(.secondary)
                if !manager.storageError.isEmpty { Text(manager.storageError).foregroundStyle(.red) }
            }

            Section("Recent observations") {
                ForEach(Array(manager.history.observations.suffix(30).reversed())) { observation in
                    observationRow(observation)
                }
            }
        }
        .navigationTitle("Activity observations")
        .onAppear { manager.refresh() }
        .confirmationDialog("Clear the local activity history and stop collecting?", isPresented: $confirmClear, titleVisibility: .visible) {
            Button("Clear history and stop collection", role: .destructive) { manager.clearHistory() }
        }
    }

    private func observationRow(_ observation: ActivityObservation) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            switch observation.kind {
            case .heartRate:
                Text("Heart rate: \(observation.value ?? 0, specifier: "%.0f") bpm")
            case .phoneSteps:
                Text("iPhone steps: \(observation.value ?? 0, specifier: "%.0f")")
            case .phoneStepInterval:
                Text("iPhone interval steps: \(observation.value ?? 0, specifier: "%.0f")")
            case .phoneMotion:
                Text("iPhone motion")
            }
            Text(observation.endDate, format: .dateTime.month().day().hour().minute().second())
            Text("Received \(observation.receivedAt.formatted(date: .abbreviated, time: .standard))")
            Text([observation.source, observation.detail].filter { !$0.isEmpty }.joined(separator: " · "))
        }
        .font(.footnote)
        .accessibilityElement(children: .combine)
    }
}

/// Encode only when sharing, rather than formatting the full history on every sensor update.
private struct ActivityObservationExport: Transferable {
    let history: ActivityObservationHistory

    static var transferRepresentation: some TransferRepresentation {
        DataRepresentation(exportedContentType: .commaSeparatedText) { export in
            Data(export.history.csv.utf8)
        }
        .suggestedFileName("Trio-activity-observations.csv")
    }
}
