import AppKit
import SwiftUI
import UniformTypeIdentifiers

@main
struct ConcurHelperApp: App {
    @StateObject private var workflow = ReceiptWorkflow()

    var body: some Scene {
        Window("Concur Helper", id: "receipt-review") {
            ReviewView(workflow: workflow)
                .frame(minWidth: 780, minHeight: 520)
                .onOpenURL(perform: workflow.receiveJob)
        }
        .defaultSize(width: 1040, height: 660)
    }
}

struct ReceiptPlan: Decodable {
    let expenses: [Expense]
    let reportObservation: ReportObservation?
}

struct Expense: Decodable, Identifiable {
    struct Candidate: Decodable {
        let path: String
        let evidence: String

        var summary: String {
            evidence == "pdf_vendor_date_total"
                ? "Merchant, date, and total found in PDF"
                : "Amount in filename. Check the receipt details."
        }
    }

    let id: String
    let merchant: String
    let date: String
    let amount: String
    let currency: String
    let paymentType: String?
    let status: String
    let attachment: String?
    let candidates: [Candidate]?

    var displayedAmount: String {
        guard let value = Decimal(string: amount, locale: Locale(identifier: "en_US_POSIX")) else {
            return "\(currency) \(amount)"
        }
        return value.formatted(.currency(code: currency))
    }

    var statusLabel: String {
        switch status {
        case "review": "Ready for review"
        case "already_attached": "Already attached"
        case "ambiguous": "Conflicting matches"
        case "manual_attachment": "Manual attachment"
        case "not_checked": "Receipt match not checked"
        default: "No matching receipt"
        }
    }
}

struct ReviewView: View {
    @ObservedObject var workflow: ReceiptWorkflow
    @State private var choosingFolder = false
    @State private var selection: String?
    @State private var uploadConfirmation = false

    private var selected: Expense? {
        workflow.expenses.first { $0.id == selection }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            VStack(alignment: .leading, spacing: 6) {
                Text("Concur Helper").font(.largeTitle.bold())
                Text("Match PCARD receipts to an existing draft expense report.")
                    .foregroundStyle(.secondary)
                if let job = workflow.job {
                    HStack {
                        Label("Juno · \(job.label) · \(job.start) through \(job.end)", systemImage: "briefcase")
                            .font(.callout.weight(.medium))
                        Spacer()
                        Button("End Job", action: workflow.endJob).disabled(workflow.busy)
                    }
                }
            }
            HStack(alignment: .bottom, spacing: 14) {
                VStack(alignment: .leading, spacing: 5) {
                    Text("Concur report URL").font(.subheadline.weight(.medium))
                    TextField("https://us2.concursolutions.com/nui/expense/reports/…",
                              text: $workflow.reportURL)
                }
                VStack(alignment: .leading, spacing: 5) {
                    Text("PCARD month folder").font(.subheadline.weight(.medium))
                    Button {
                        choosingFolder = true
                    } label: {
                        Label(workflow.folder?.lastPathComponent ?? "Choose folder", systemImage: "folder")
                    }
                    .help(workflow.folder?.path ?? "Select the folder containing this month’s receipts.")
                }
                Button("Read Report Status", action: workflow.readReport)
                    .disabled(!workflow.canReadReport)
                Button("Find Matches", action: workflow.scan)
                    .buttonStyle(.borderedProminent)
                    .disabled(!workflow.canScan)
            }
            .disabled(workflow.busy)
            Divider()
            if let report = workflow.reportObservation, let state = report.allocationState {
                Text(report.sourceStatus + " · " +
                     (state == "verified"
                      ? (report.orgTotals ?? []).map { "\($0.org) · \(report.currency ?? "") \($0.amount)" }.joined(separator: "   |   ")
                      : "Org totals unavailable in Concur’s allocation summary"))
                    .font(.callout)
                    .foregroundStyle(.secondary)
            }
            if !workflow.paymentTotals.isEmpty {
                Text(workflow.paymentTotals.joined(separator: "   |   "))
                    .font(.callout.monospacedDigit()).foregroundStyle(.secondary)
                    .accessibilityLabel("Recorded payment totals: " + workflow.paymentTotals.joined(separator: ", "))
            }
            HSplitView {
                if workflow.expenses.isEmpty {
                    ContentUnavailableView("No expenses to review", systemImage: "doc.text.magnifyingglass",
                                           description: Text("Choose a folder and scan a Concur draft."))
                        .frame(minWidth: 320, maxWidth: .infinity)
                } else {
                    List(workflow.expenses, selection: $selection) { expense in
                        HStack(spacing: 12) {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(expense.merchant).fontWeight(.medium)
                                Text("\(expense.date) · \(workflow.label(for: expense))")
                                    .font(.caption).foregroundStyle(.secondary)
                            }
                            Spacer()
                            Text(expense.displayedAmount).monospacedDigit()
                        }
                        .tag(expense.id)
                    }
                    .frame(minWidth: 320)
                }
                Group {
                    if let expense = selected {
                        receiptDetail(expense)
                    } else {
                        ContentUnavailableView("Select an expense", systemImage: "doc.text",
                                               description: Text("Inspect its receipt and match evidence here."))
                    }
                }
                .frame(minWidth: 310, maxWidth: .infinity, maxHeight: .infinity)
            }
            Divider()
            HStack {
                if workflow.busy {
                    ProgressView().controlSize(.small)
                }
                Text(workflow.message).font(.callout)
                    .foregroundStyle(workflow.failed ? Color.red : Color.secondary)
                    .textSelection(.enabled)
                Spacer()
                if workflow.canExport {
                    Button("Export for Juno…") {
                        let panel = NSSavePanel()
                        panel.allowedContentTypes = [.json]
                        panel.nameFieldStringValue = "concur-review.json"
                        if panel.runModal() == .OK, let url = panel.url {
                            workflow.exportForJuno(to: url)
                        }
                    }
                }
                if workflow.needsSignIn {
                    Button("Continue after SSO", action: workflow.continueAfterSignIn)
                }
                if workflow.busy {
                    Button("Cancel", action: workflow.cancel)
                }
            }
        }
        .padding(22)
        .fileImporter(isPresented: $choosingFolder, allowedContentTypes: [.folder]) { result in
            workflow.chooseFolder(result)
        }
        .fileDialogDefaultDirectory(FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Desktop/PCARD", isDirectory: true))
        .confirmationDialog("Attach this receipt to the selected expense?", isPresented: $uploadConfirmation) {
            if let expense = selected {
                Button("Attach and Verify") { workflow.upload(expense) }
            }
        } message: {
            if let expense = selected {
                Text("\(expense.merchant) · \(expense.displayedAmount) · \(expense.date)")
            }
        }
        .onChange(of: workflow.expenses.map(\.id)) { _, ids in
            if !ids.contains(selection ?? "") { selection = ids.first }
        }
    }

    private func receiptDetail(_ expense: Expense) -> some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                Text(expense.merchant).font(.title2.bold())
                Text("\(expense.displayedAmount) · \(expense.date) · \(expense.paymentType ?? "Payment type unavailable")")
                    .foregroundStyle(.secondary)
                Text(workflow.label(for: expense)).font(.headline)
                ForEach(expense.candidates ?? [], id: \.path) { candidate in
                    VStack(alignment: .leading, spacing: 6) {
                        Button {
                            NSWorkspace.shared.open(URL(fileURLWithPath: candidate.path))
                        } label: {
                            Label(URL(fileURLWithPath: candidate.path).lastPathComponent, systemImage: "doc")
                        }
                        Text(candidate.summary).font(.callout).foregroundStyle(.secondary)
                    }
                }
                if expense.status == "ambiguous" {
                    Text("Review the candidates in Concur or narrow the folder and scan again.")
                        .foregroundStyle(.secondary)
                }
                if expense.status == "manual_attachment" {
                    Text("Use Concur’s expense editor for this receipt.")
                        .foregroundStyle(.secondary)
                }
                if workflow.canUpload(expense) {
                    Button("Review Upload…") { uploadConfirmation = true }
                        .buttonStyle(.borderedProminent)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(18)
        }
    }
}
