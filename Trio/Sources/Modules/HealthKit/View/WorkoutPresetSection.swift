import CoreData
import SwiftUI

struct WorkoutPresetSection: View {
    @ObservedObject var manager: WorkoutPresetManager
    @FetchRequest(
        entity: OverrideStored.entity(), sortDescriptors: [NSSortDescriptor(key: "orderPosition", ascending: true)],
        predicate: NSPredicate(format: "isPreset == YES")
    ) private var overrides: FetchedResults<OverrideStored>
    @FetchRequest(
        entity: TempTargetStored.entity(), sortDescriptors: [NSSortDescriptor(key: "orderPosition", ascending: true)],
        predicate: NSPredicate(format: "isPreset == YES")
    ) private var targets: FetchedResults<TempTargetStored>

    private var selectionExists: Bool {
        switch manager.configuration.kind {
        case .override: overrides.contains { $0.id == manager.configuration.presetID }
        case .tempTarget: targets.contains { $0.id?.uuidString == manager.configuration.presetID }
        }
    }

    var body: some View {
        Section("Workout preset automation") {
            Picker("Preset type", selection: Binding(
                get: { manager.configuration.kind },
                set: { manager.select(kind: $0, id: "") }
            )) {
                Text("Override").tag(ActivityPresetKind.override)
                Text("Temporary target").tag(ActivityPresetKind.tempTarget)
            }
            Picker("Activity preset", selection: Binding(
                get: { manager.configuration.presetID },
                set: { manager.select(kind: manager.configuration.kind, id: $0) }
            )) {
                Text("Select a saved preset").tag("")
                if manager.configuration.kind == .override {
                    ForEach(overrides) { preset in
                        if let id = preset.id { Text(preset.name ?? id).tag(id) }
                    }
                } else {
                    ForEach(targets) { preset in
                        if let id = preset.id { Text(preset.name ?? id.uuidString).tag(id.uuidString) }
                    }
                }
            }
            Toggle("Allow workout preset activation", isOn: Binding(
                get: { manager.configuration.isEnabled },
                set: { manager.setEnabled($0) }
            ))
            .disabled(!selectionExists && !manager.configuration.isEnabled)
            if !selectionExists, !manager.configuration.presetID.isEmpty {
                Text("The selected preset is no longer available. Select a saved preset again.")
                    .font(.footnote).foregroundStyle(.secondary)
            }
            Text("Uses the preset’s saved settings and duration, including indefinite duration if configured. Never replaces an enabled override or temporary target. Repeated starts leave the running adjustment unchanged. Ending a workout does not cancel the preset.")
                .font(.footnote).foregroundStyle(.secondary)
            Text("In the iPhone Shortcuts app, create an Apple Watch Workout automation for Starts. Choose Run Immediately and add Trio’s Activate workout preset action. This one-time setup is required; collecting observations alone does not enable activation.")
                .font(.footnote)
            Text("Successful activations use Trio’s existing Nightscout upload settings. Configure Override Start or Temp Target Start alarms in LoopFollow for parent notifications; internet and follower updates are required.")
                .font(.footnote).foregroundStyle(.secondary)
            if !manager.lastResult.isEmpty { Text(manager.lastResult).font(.footnote) }
        }
    }
}
