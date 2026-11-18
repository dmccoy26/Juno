import Foundation

@MainActor
final class ReceiptWorkflow: ObservableObject {
    @Published var reportURL = UserDefaults.standard.string(forKey: "reportURL") ?? ""
    @Published private(set) var folder = UserDefaults.standard.url(forKey: "pcardFolder")
    @Published private(set) var expenses: [Expense] = []
    @Published private(set) var busy = false
    @Published private(set) var needsSignIn = false
    @Published private(set) var failed = false
    @Published private(set) var job = ReconciliationJob.saved
    @Published private(set) var message = "Open a draft in Concur, then paste its report URL."

    private enum Operation {
        case scan(URL, readOnly: Bool)
        case upload(String)
    }

    private var operation: Operation?
    private var process: Process?
    private var processInput: Pipe?
    private var processLog: URL?
    private var monitor: Task<Void, Never>?
    private var reviewDirectory: URL?
    private var planFile: URL?
    private var scannedReport: String?
    private var scannedFolder: URL?
    private var verified: Set<String> = []
    private var cancelled = false
    private var rescanRequired = false
    @Published private(set) var reportObservation: ReportObservation?
    private var exportRuns: [ExportRun] = []
    private var uncertain: Set<String> = []
    private var operationStartedAt = Date()

    private var normalizedReport: String? {
        let value = reportURL.trimmingCharacters(in: .whitespacesAndNewlines)
        let pattern = #"^https://us2\.concursolutions\.com/(?:nui/expense/reports|goto/expense-report)/([A-Z0-9]+)$"#
        guard let range = value.range(of: pattern, options: .regularExpression),
              range == value.startIndex..<value.endIndex,
              let id = value.split(separator: "/").last else { return nil }
        return "https://us2.concursolutions.com/nui/expense/reports/\(id)"
    }

    var canReadReport: Bool { !busy && normalizedReport != nil }
    var canScan: Bool { canReadReport && folder != nil }

    func receiveJob(_ url: URL) {
        guard let request = ReconciliationJob(url: url) else { return }
        if request == job { return }
        guard !busy, job == nil else {
            show("Finish the current reconciliation before opening another Juno request.", failed: true)
            return
        }
        clearReview()
        job = request
        request.persist()
        reportURL = ""
        UserDefaults.standard.removeObject(forKey: "reportURL")
        let root = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Desktop/PCARD")
        if request.start.prefix(7) == request.end.prefix(7) {
            folder = request.monthFolder(in: root)
        } else {
            folder = nil
        }
        UserDefaults.standard.set(folder, forKey: "pcardFolder")
        show("Juno requested a reconciliation. Open the matching draft and confirm the PCARD folder.")
    }

    func endJob() {
        guard !busy else { return }
        clearReview()
        job = nil
        UserDefaults.standard.removeObject(forKey: ReconciliationJob.storageKey)
        show("Juno request closed.")
    }

    var canExport: Bool {
        !busy && !exportRuns.isEmpty && scannedReport == normalizedReport && scannedFolder == folder
    }

    var paymentTotals: [String] {
        let grouped = Dictionary(grouping: expenses) {
            PaymentGroup(type: $0.paymentType ?? "Unknown payment type", currency: $0.currency)
        }
        return grouped.keys.sorted { ($0.type, $0.currency) < ($1.type, $1.currency) }.map { key in
            let rows = grouped[key, default: []]
            let amount = rows.reduce(Decimal.zero) { total, row in
                total + (Decimal(string: row.amount, locale: Locale(identifier: "en_US_POSIX")) ?? 0)
            }
            return "\(key.type) · \(rows.count) entries · \(amount.formatted(.currency(code: key.currency)))"
        }
    }

    private struct PaymentGroup: Hashable {
        let type: String
        let currency: String
    }

    func exportForJuno(to url: URL) {
        guard canExport, let scannedReport else { return }
        do {
            let export = JunoExport(reportURL: scannedReport, job: job,
                                    observation: reportObservation, expenses: expenses,
                                    verified: verified, uncertain: uncertain, runs: exportRuns)
            try export.write(to: url)
            if export.expenses == nil {
                show("Report status and run details exported. Import in Juno Purchasing; previous expense rows and their scan date are kept.")
            } else {
                show("Export ready. In Juno, open Purchasing and choose Import helper export.")
            }
        } catch {
            show("Could not export the reconciliation: \(error.localizedDescription)", failed: true)
        }
    }

    func chooseFolder(_ result: Result<URL, Error>) {
        switch result {
        case .success(let url):
            folder = url.standardizedFileURL
            UserDefaults.standard.set(folder, forKey: "pcardFolder")
        case .failure(let error):
            let nsError = error as NSError
            if nsError.domain != NSCocoaErrorDomain || nsError.code != NSUserCancelledError {
                show(error.localizedDescription, failed: true)
            }
        }
    }

    func label(for expense: Expense) -> String {
        verified.contains(expense.id) ? "Attachment verified in Concur" : expense.statusLabel
    }

    func canUpload(_ expense: Expense) -> Bool {
        !busy && !rescanRequired && scannedReport == normalizedReport && scannedFolder == folder
            && expense.status == "review" && expense.attachment != nil && !verified.contains(expense.id)
    }

    func scan() { startScan(readOnly: false) }

    func readReport() { startScan(readOnly: true) }

    private func startScan(readOnly: Bool) {
        guard readOnly ? canReadReport : canScan, let report = normalizedReport else { return }
        clearReview()
        do {
            let dir = try privateDirectory(under: FileManager.default.temporaryDirectory)
            reviewDirectory = dir
            let output = dir.appendingPathComponent("plan.json")
            var arguments = ["report-read", report, output.path]
            if !readOnly, let folder {
                arguments = ["pcard-scan", report, folder.path, output.path]
                if let job { arguments += ["--start", job.start, "--end", job.end] }
            }
            try run(.scan(output, readOnly: readOnly), arguments: arguments,
                    message: readOnly ? "Reading Concur report status and allocations…"
                                      : "Opening the Concur draft and scanning receipts…")
            scannedReport = report
            scannedFolder = folder
            UserDefaults.standard.set(report, forKey: "reportURL")
        } catch {
            clearReview()
            show(error.localizedDescription, failed: true)
        }
    }

    func upload(_ expense: Expense) {
        guard canUpload(expense), let planFile else { return }
        do {
            try run(.upload(expense.id), arguments: ["attach", planFile.path, expense.id],
                    message: "Attaching and verifying the receipt in Concur…")
        } catch {
            show(error.localizedDescription, failed: true)
        }
    }

    func continueAfterSignIn() {
        guard needsSignIn, let processInput else { return }
        do {
            try processInput.fileHandleForWriting.write(contentsOf: Data("\n".utf8))
            if let processLog, let log = try? Data(contentsOf: processLog) {
                seenPrompts = promptCount(in: log)
            }
            needsSignIn = false
            show("Checking the signed-in Concur browser…")
        } catch {
            show("The browser session ended. Scan the draft again.", failed: true)
        }
    }

    func cancel() {
        guard let process, process.isRunning, !cancelled else { return }
        cancelled = true
        needsSignIn = false
        process.terminate()
        show("Stopping the current operation…")
    }

    private var seenPrompts = 0

    private func promptCount(in data: Data) -> Int {
        String(decoding: data, as: UTF8.self).components(separatedBy: "CONCUR_SSO_REQUIRED").count - 1
    }

    private func run(_ operation: Operation, arguments: [String], message: String) throws {
        guard let resources = Bundle.main.resourceURL,
              let pythonPath = try? String(contentsOf: resources.appendingPathComponent("python-path.txt"),
                                           encoding: .utf8).trimmingCharacters(in: .whitespacesAndNewlines),
              FileManager.default.isExecutableFile(atPath: pythonPath) else {
            throw WorkflowError("Run build-mac-app.sh to package the app with your installed Python environment.")
        }
        guard let reviewDirectory else { throw WorkflowError("Scan the draft again.") }
        let support = try FileManager.default.url(for: .applicationSupportDirectory, in: .userDomainMask,
                                                   appropriateFor: nil, create: true)
            .appendingPathComponent("Concur Helper", isDirectory: true)
        try FileManager.default.createDirectory(at: support, withIntermediateDirectories: true,
                                                attributes: [.posixPermissions: 0o700])
        let log = reviewDirectory.appendingPathComponent("worker.log")
        try Data().write(to: log)
        let writer = try FileHandle(forWritingTo: log)
        defer { try? writer.close() }
        let input = Pipe()
        let worker = Process()
        worker.executableURL = URL(fileURLWithPath: pythonPath)
        worker.arguments = ["-u", resources.appendingPathComponent("concur_portal.py").path,
                            "--profile", support.appendingPathComponent("Browser").path] + arguments
        worker.standardInput = input
        worker.standardOutput = writer
        worker.standardError = writer
        try worker.run()

        self.operation = operation
        operationStartedAt = Date()
        process = worker
        processInput = input
        processLog = log
        seenPrompts = 0
        cancelled = false
        busy = true
        show(message)

        monitor = Task { [weak self] in
            while !Task.isCancelled {
                if self?.poll() != true { return }
                try? await Task.sleep(for: .milliseconds(250))
            }
        }
    }

    private func poll() -> Bool {
        guard let process, let operation, let processLog else { return false }
        let log = (try? Data(contentsOf: processLog)) ?? Data()
        if process.isRunning {
            if !cancelled && promptCount(in: log) > seenPrompts {
                needsSignIn = true
                show("Sign in to your university account in the Concur browser, then continue here.")
            }
            return true
        }

        busy = false
        needsSignIn = false
        self.process = nil
        self.operation = nil
        try? processInput?.fileHandleForWriting.close()
        processInput = nil

        if cancelled || process.terminationStatus != 0 {
            rememberRun(operation, log: log, succeeded: false)
            let text = String(decoding: log, as: UTF8.self)
            let error = text.split(separator: "\n").last { $0.hasPrefix("CONCUR_ERROR: ") }
                .map { String($0.dropFirst("CONCUR_ERROR: ".count)) }
            switch operation {
            case .scan:
                show(cancelled ? "Scan cancelled." : error ?? "Could not scan the Concur draft. Check the browser session.",
                     failed: !cancelled)
            case .upload(let id):
                uncertain.insert(id)
                rescanRequired = true
                show((error.map { $0 + " " } ?? "") +
                     "Upload was not verified. Scan the draft again before retrying.", failed: true)
            }
            return false
        }

        switch operation {
        case .scan(let url, let readOnly):
            do {
                let decoder = JSONDecoder()
                decoder.keyDecodingStrategy = .convertFromSnakeCase
                let plan = try decoder.decode(ReceiptPlan.self, from: Data(contentsOf: url))
                expenses = plan.expenses
                reportObservation = plan.reportObservation
                rememberRun(operation, log: log, succeeded: true)
                planFile = url
                let matches = expenses.filter { $0.status == "review" }.count
                if readOnly {
                    show("Read \(expenses.count) expenses · \(plan.reportObservation?.sourceStatus ?? "Status unavailable")")
                } else {
                    show("\(expenses.count) expenses · \(matches) ready for review")
                }
            } catch {
                rememberRun(operation, log: log, succeeded: false)
                show("The scan completed but its review plan could not be opened.", failed: true)
            }
        case .upload(let id):
            rememberRun(operation, log: log, succeeded: true)
            verified.insert(id)
            show("Receipt verified on the expense after reloading Concur.")
        }
        return false
    }

    private func rememberRun(_ operation: Operation, log: Data, succeeded: Bool) {
        let text = String(decoding: log, as: UTF8.self)
        let reportRead = text.contains("CONCUR_REPORT_READ")
        let signInState: String
        if promptCount(in: log) == 0 {
            signInState = succeeded ? "not_required" : "unknown"
        } else {
            signInState = succeeded || reportRead ? "completed_manually" : "manual_sign_in_needed"
        }
        let kind: String
        let coverage: [String: ExportRun.SourceState]
        let partial: Bool
        switch operation {
        case .scan(_, let readOnly):
            kind = readOnly ? "read_report_status" : "scan"
            partial = !succeeded && reportRead
            coverage = ["concur": succeeded || reportRead ? .complete : .failed,
                        "pcard": readOnly ? .notSearched : succeeded ? .complete : reportRead ? .failed : .notSearched,
                        "gmail": .notSearched, "orders": .notSearched]
        case .upload:
            kind = "attach_and_verify"
            partial = false
            coverage = ["concur": succeeded ? .complete : .failed, "gmail": .notSearched, "orders": .notSearched]
        }
        exportRuns.append(ExportRun(operation: kind, startedAt: operationStartedAt, endedAt: Date(),
                                    outcome: succeeded ? "success" : partial ? "partial" : "failure",
                                    coverage: coverage, signInState: signInState))
    }

    private func clearReview() {
        if let reviewDirectory { try? FileManager.default.removeItem(at: reviewDirectory) }
        reviewDirectory = nil
        planFile = nil
        reportObservation = nil
        exportRuns = []
        uncertain = []
        expenses = []
        verified = []
        rescanRequired = false
    }

    private func privateDirectory(under parent: URL) throws -> URL {
        let dir = parent.appendingPathComponent("ConcurHelper-\(UUID().uuidString)", isDirectory: true)
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: false,
                                                attributes: [.posixPermissions: 0o700])
        return dir
    }

    private func show(_ message: String, failed: Bool = false) {
        self.message = message
        self.failed = failed
    }
}

private struct WorkflowError: LocalizedError {
    let errorDescription: String?
    init(_ message: String) { errorDescription = message }
}
