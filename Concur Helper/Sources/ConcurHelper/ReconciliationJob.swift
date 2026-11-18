import Foundation

struct ReconciliationJob: Codable, Equatable {
    static let storageKey = "junoReconciliationJob"
    let id: UUID
    let period: String
    let start: String
    let end: String

    var label: String { period == "week" ? "Weekly reconciliation" : "Monthly reconciliation" }

    init?(url: URL) {
        guard let components = URLComponents(url: url, resolvingAgainstBaseURL: false),
              components.scheme == "concur-helper", components.host == "reconcile",
              components.path.isEmpty,
              components.queryItems?.count == 4 else { return nil }
        func value(_ name: String) -> String? {
            components.queryItems?.first(where: { $0.name == name })?.value
        }
        guard let rawID = value("id"), let id = UUID(uuidString: rawID),
              let period = value("period"), period == "week" || period == "month",
              let start = value("start"), let end = value("end") else { return nil }
        let formatter = Self.formatter("yyyy-MM-dd")
        guard let first = formatter.date(from: start), let last = formatter.date(from: end),
              formatter.string(from: first) == start, formatter.string(from: last) == end,
              first <= last, last.timeIntervalSince(first) < 32 * 86400 else { return nil }
        self.id = id
        self.period = period
        self.start = start
        self.end = end
    }

    static var saved: Self? {
        guard let data = UserDefaults.standard.data(forKey: storageKey) else { return nil }
        return try? JSONDecoder().decode(Self.self, from: data)
    }

    func persist() {
        if let data = try? JSONEncoder().encode(self) {
            UserDefaults.standard.set(data, forKey: Self.storageKey)
        }
    }

    func monthFolder(in root: URL) -> URL? {
        guard let date = Self.formatter("yyyy-MM-dd").date(from: start),
              let folders = try? FileManager.default.contentsOfDirectory(at: root,
                includingPropertiesForKeys: [.isDirectoryKey], options: [.skipsHiddenFiles]) else { return nil }
        var names = Set(["MMMM yyyy", "MMM yyyy"].map { Self.formatter($0).string(from: date).lowercased() })
        if names.contains(where: { $0.hasPrefix("sep ") }) {
            names.insert(Self.formatter("MMM yyyy").string(from: date).lowercased()
                .replacingOccurrences(of: "sep ", with: "sept "))
        }
        let matches = folders.filter { folder in
            names.contains(folder.lastPathComponent.lowercased())
                && (try? folder.resourceValues(forKeys: [.isDirectoryKey]).isDirectory) == true
        }
        return matches.count == 1 ? matches.first : nil
    }

    private static func formatter(_ format: String) -> DateFormatter {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = TimeZone(identifier: "America/Chicago")
        formatter.dateFormat = format
        return formatter
    }
}
