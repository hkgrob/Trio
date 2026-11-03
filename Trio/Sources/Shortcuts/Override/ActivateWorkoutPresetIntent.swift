import AppIntents
import Foundation

/// Connect to Shortcuts → Automation → Apple Watch Workout → Starts → Run Immediately.
struct ActivateWorkoutPresetIntent: AppIntent {
    static var title: LocalizedStringResource = "Activate workout preset"
    static var description = IntentDescription(
        "Activate the activity preset selected in Trio, preserving any existing override or temporary target. Requires separate opt-in in Trio."
    )

    @MainActor func perform() async throws -> some ProvidesDialog {
        // A workout automation may launch Trio while its stores are still loading.
        try await CoreDataStack.shared.initializeStack()
        let result = await TrioApp.resolver.resolve(WorkoutPresetManager.self)!.activateFromWorkout()
        return .result(dialog: IntentDialog(stringLiteral: result))
    }
}
