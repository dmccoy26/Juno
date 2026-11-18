import CryptoKit
import Foundation

struct OrgTotal: Codable, Identifiable {
    let org: String
    let amount: String
    var id: String { org }
}

struct ReportObservation: Decodable {
    let sourceStatus: String
    let observedAt: String
    let title: String?
    let periodStart: String?
    let periodEnd: String?
    let currency: String?
    let total: String?
    let allocationState: String?
    let orgTotals: [OrgTotal]?
}

struct ExportRun: Encodable {
    enum SourceState: String, Encodable {
        case complete, failed
        case notSearched = "not_searched"
    }

    let id = UUID()
    let operation: String
    let startedAt: Date
    let endedAt: Date
    let outcome: String
    let coverage: [String: SourceState]
    let signInState: String
}

struct JunoExport: Encodable {
    struct Period: Encodable {
        let state: String
        let start: String?
        let end: String?

        init(_ job: ReconciliationJob?) {
            self.init(start: job?.start, end: job?.end)
        }

        init(start: String?, end: String?) {
            self.state = start == nil || end == nil ? "unknown" : "observed"
            self.start = start
            self.end = end
        }
    }

    struct Report: Encodable {
        let id: String
        let sourceStatus: String
        let observedAt: String
        let title: String?
        let reportingPeriod: Period
        let currency: String?
        let total: String?
        let allocationState: String
        let orgTotals: [OrgTotal]

        let submissionTimeState = "not_searched"
    }

    struct Row: Encodable {
        let id: String
        let reportId: String
        let merchant: String
        let date: String
        let amount: String
        let currency: String
        let status: String
        let receiptSearchOutcome: String
        let statementIdState = "not_searched"
        let accountCodingStatus = "not_searched"
        let externalReferenceState = "not_searched"
    }

    let schemaVersion = 1
    let helperInstanceId: UUID
    let exportId = UUID()
    let createdAt = Date()
    let observationWindow: Period
    let completeness: [String: String]
    let expenses: [Row]?
    let reports: [Report]
    let orders: [String] = []
    let runs: [ExportRun]

    init(reportURL: String, job: ReconciliationJob?, observation: ReportObservation?,
         expenses: [Expense], verified: Set<String>, uncertain: Set<String>, runs: [ExportRun]) {
        let instance = Self.instanceID()
        helperInstanceId = instance
        // The requested window is distinct from the report's observed accounting period.
        observationWindow = Period(job)
        let reportID = SHA256.hash(data: Data("\(instance.uuidString)|\(reportURL)".utf8))
            .map { String(format: "%02x", $0) }.joined()
        let scan = runs.last { $0.operation == "scan" }
        self.expenses = scan?.outcome == "success" ? expenses.map { expense in
            let status: String
            let outcome: String
            if uncertain.contains(expense.id) {
                status = "not_checked"
                outcome = "unknown"
            } else if verified.contains(expense.id) || expense.status == "already_attached" {
                status = "already_attached"
                outcome = "already_attached"
            } else if ["manual_attachment", "not_checked"].contains(expense.status) {
                status = "not_checked"
                outcome = "not_searched"
            } else {
                status = expense.status
                outcome = expense.status
            }
            return Row(id: expense.id, reportId: reportID, merchant: expense.merchant,
                       date: expense.date, amount: expense.amount, currency: expense.currency,
                       status: status, receiptSearchOutcome: outcome)
        } : nil
        reports = observation.map {
            [Report(id: reportID, sourceStatus: $0.sourceStatus, observedAt: $0.observedAt,
                    title: $0.title, reportingPeriod: Period(start: $0.periodStart, end: $0.periodEnd),
                    currency: $0.currency, total: $0.total, allocationState: $0.allocationState ?? "not_searched",
                    orgTotals: $0.orgTotals ?? [])]
        } ?? []
        self.runs = runs
        let hasPartialRows = expenses.contains { ["manual_attachment", "not_checked"].contains($0.status) } || !uncertain.isEmpty
        completeness = [
            "expenses": scan?.outcome == "success" ? (hasPartialRows ? "partial" : "complete") : "unknown",
            "reports": observation == nil ? "unknown" : "partial",
            "orders": "not_searched",
            "runs": "current_session"
        ]
    }

    private enum CodingKeys: String, CodingKey {
        case schemaVersion, helperInstanceId, exportId, createdAt, observationWindow
        case completeness, expenses, reports, orders, runs
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(schemaVersion, forKey: .schemaVersion)
        try container.encode(helperInstanceId, forKey: .helperInstanceId)
        try container.encode(exportId, forKey: .exportId)
        try container.encode(createdAt, forKey: .createdAt)
        try container.encode(observationWindow, forKey: .observationWindow)
        try container.encode(completeness, forKey: .completeness)
        try container.encode(expenses, forKey: .expenses)
        try container.encode(reports, forKey: .reports)
        try container.encode(orders, forKey: .orders)
        try container.encode(runs, forKey: .runs)
    }

    func write(to destination: URL) throws {
        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        encoder.dateEncodingStrategy = .iso8601
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        try encoder.encode(self).write(to: destination, options: .atomic)
    }

    private static func instanceID() -> UUID {
        let key = "junoExportHelperInstanceID"
        if let stored = UserDefaults.standard.string(forKey: key),
           let id = UUID(uuidString: stored) { return id }
        let id = UUID()
        UserDefaults.standard.set(id.uuidString, forKey: key)
        return id
    }
}
