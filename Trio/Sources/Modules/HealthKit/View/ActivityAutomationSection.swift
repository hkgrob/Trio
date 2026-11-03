import SwiftUI

struct ActivityAutomationSection: View {
    @ObservedObject var manager: ActivityAutomationManager
    @ObservedObject var observations: ActivityObservationManager

    var body: some View {
        Section("Automatic activity preset") {
            Text(
                "Fresh Apple Watch heart rate takes precedence. iPhone step rate is used only when Watch heart rate is missing or stale."
            )
            .font(.footnote)
            thresholdField("Watch heart-rate threshold (bpm)", keyPath: \.heartRateBPM)
            thresholdField("iPhone fallback threshold (steps/min)", keyPath: \.stepsPerMinute)
            thresholdField("Required activity duration (minutes)", keyPath: \.sustainedMinutes)
            thresholdField("Required recovery duration (minutes)", keyPath: \.recoveryMinutes)
            thresholdField("Maximum reading age and gap (minutes)", keyPath: \.maximumGapMinutes)
            Text("The reading age and gap must be at least one minute because iPhone step intervals span one minute.")
                .font(.footnote).foregroundStyle(.secondary)
            Toggle("Automatically activate activity preset", isOn: Binding(
                get: { manager.configuration.isEnabled },
                set: { manager.setEnabled($0) }
            ))
                .disabled(!manager.canEnable && !manager.configuration.isEnabled)
            if !manager.canEnable {
                Text(
                    "Enable collection, select a saved activity preset above, and enter positive thresholds and durations before enabling automation."
                )
                .font(.footnote).foregroundStyle(.secondary)
            }
            if manager.configuration.isEnabled {
                Text(statusText).font(.footnote)
                if let source = manager.source {
                    Text(source == .watch ? "Using Apple Watch heart rate" : "Using iPhone step-rate fallback")
                        .font(.footnote).foregroundStyle(.secondary)
                }
                if manager.isActivating { ProgressView("Activating activity preset…") }
            }
            Text(
                "Uses the saved activity preset above, independently of the workout shortcut toggle. Triggers once per activity episode. Fresh readings below the threshold must span the recovery duration before another trigger is allowed. Missing readings do not count as recovery. Switching data sources restarts the duration window."
            )
            .font(.footnote).foregroundStyle(.secondary)
            Text(
                "Any enabled override or temporary target is preserved. Manual adjustment changes block reactivation until recovery. Changing a threshold or preset, or turning collection off, disables automation until you explicitly enable it again."
            )
            .font(.footnote).foregroundStyle(.secondary)
            Text(
                "Passive sensor delivery can be delayed while Trio is backgrounded. Old readings cannot trigger activation. This feature detects configured activity signals; it does not predict glucose or choose insulin doses."
            )
            .font(.footnote).foregroundStyle(.secondary)
        }
    }

    private var statusText: String {
        switch manager.phase {
        case .waitingForData:
            return String(localized: "Waiting for fresh sensor data.")
        case .waitingForActivity:
            return String(localized: "Ready. Waiting for the configured activity threshold.")
        case let .qualifying(seconds):
            return String(localized: "Activity qualifying: \(Int(seconds)) seconds of sustained evidence.")
        case .latched:
            return String(localized: "This episode is blocked from further activation. Waiting for fresh recovery evidence.")
        case let .recovering(seconds):
            return String(localized: "Recovery qualifying: \(Int(seconds)) seconds of sustained evidence.")
        }
    }

    private func thresholdField(
        _ title: LocalizedStringKey,
        keyPath: WritableKeyPath<ActivityAutomationConfiguration, Double?>
    ) -> some View {
        HStack {
            Text(title)
            Spacer()
            TextField("Required", value: Binding(
                get: { manager.configuration[keyPath: keyPath] },
                set: { value in manager.update { $0[keyPath: keyPath] = value } }
            ), format: .number)
                .keyboardType(.decimalPad)
                .multilineTextAlignment(.trailing)
                .frame(maxWidth: 100)
                .accessibilityLabel(title)
        }
    }
}
