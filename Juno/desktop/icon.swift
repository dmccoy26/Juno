import Foundation

// The approved generated identity is the single source for every icon size.
// Builders resize this master into the complete native macOS iconset.
let source = URL(fileURLWithPath: #filePath).deletingLastPathComponent()
    .appendingPathComponent("branding/juno-app-icon.png")
try Data(contentsOf: source).write(to: URL(fileURLWithPath: CommandLine.arguments[1]))
