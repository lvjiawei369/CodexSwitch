import Foundation
import AppKit

class Manager: ObservableObject {
    @Published var apiKey: String = ""
    @Published var selectedModel: String = "deepseek-v4-pro"
    @Published var isEnabled: Bool = false
    @Published var statusText: String = "已停止"
    @Published var isLoading: Bool = false

    private var moonProcess: Process?
    private let configDir = FileManager.default.homeDirectoryForCurrentUser
        .appendingPathComponent(".codex-switch")
    private let codexHome = FileManager.default.homeDirectoryForCurrentUser
        .appendingPathComponent(".codex")
    private let port = "38440"

    init() { loadSettings() }

    // Call from any thread; dispatches UI updates to main
    func toggle() {
        setMain(\.isLoading, true)
        Task.detached { [self] in
            if await MainActor.run(body: { self.isEnabled }) {
                await self.startDeepSeek()
            } else {
                await MainActor.run { self.stopDeepSeek() }
            }
            await MainActor.run { self.isLoading = false }
        }
    }

    private func startDeepSeek() async {
        setMain(\.statusText, "启动中...")
        do {
            try writeConfig()

            let binary = moonBridgePath()
            let configPath = configDir.appendingPathComponent("config.yml").path

            // Backup existing Codex config
            let codexConfig = codexHome.appendingPathComponent("config.toml")
            let backupPath = configDir.appendingPathComponent("config.toml.backup")
            if FileManager.default.fileExists(atPath: codexConfig.path) &&
               !FileManager.default.fileExists(atPath: backupPath.path) {
                try FileManager.default.copyItem(at: codexConfig, to: backupPath)
            }

            let p = Process()
            p.executableURL = URL(fileURLWithPath: binary)
            p.arguments = ["--config", configPath]
            p.standardOutput = FileHandle.nullDevice
            p.standardError = FileHandle.nullDevice
            try p.run()
            await MainActor.run { self.moonProcess = p }

            guard await waitForPort() else {
                setMain(\.statusText, "启动超时")
                p.terminate()
                await MainActor.run {
                    self.moonProcess = nil
                    self.isEnabled = false
                }
                return
            }

            try await generateCodexConfig()
            setMain(\.statusText, "运行中")
        } catch {
            setMain(\.statusText, "启动失败: \(error.localizedDescription)")
            await MainActor.run {
                self.moonProcess?.terminate()
                self.moonProcess = nil
                self.isEnabled = false
            }
        }
    }

    private func stopDeepSeek() {
        moonProcess?.terminate()
        moonProcess = nil
        restoreCodexConfig()
        statusText = "已停止"
    }

    private func setMain<V>(_ kp: ReferenceWritableKeyPath<Manager, V>, _ val: V) {
        DispatchQueue.main.async { [weak self] in self?[keyPath: kp] = val }
    }

    // MARK: - Config

    private func writeConfig() throws {
        try FileManager.default.createDirectory(at: configDir, withIntermediateDirectories: true)
        let yaml = buildMoonBridgeConfig()
        try yaml.write(to: configDir.appendingPathComponent("config.yml"), atomically: true, encoding: .utf8)
    }

    private func buildMoonBridgeConfig() -> String {
        let model: String
        let display: String
        switch selectedModel {
        case "deepseek-v4-flash":
            model = "deepseek-v4-flash"; display = "DeepSeek V4 Flash"
        default:
            model = "deepseek-v4-pro"; display = "DeepSeek V4 Pro"
        }
        return """
        mode: "Transform"

        server:
          addr: "127.0.0.1:\(port)"

        defaults:
          model: "\(model)"

        models:
          \(model):
            context_window: 1000000
            max_output_tokens: 384000
            display_name: "\(display)"
            default_reasoning_level: "high"
            supported_reasoning_levels:
              - effort: "high"
                description: "High reasoning effort"
              - effort: "xhigh"
                description: "Extra high reasoning effort"
            supports_reasoning_summaries: true
            default_reasoning_summary: "auto"
            extensions:
              deepseek_v4:
                enabled: true

        providers:
          deepseek:
            base_url: "https://api.deepseek.com/anthropic"
            api_key: "\(apiKey)"
            version: "2023-06-01"
            user_agent: "moonbridge/1.0"
            offers:
              - model: \(model)

        routes:
          \(model):
            model: \(model)
            provider: deepseek
        """
    }

    private func generateCodexConfig() async throws {
        let binary = moonBridgePath()
        let configPath = configDir.appendingPathComponent("config.yml").path
        let model = await MainActor.run { self.selectedModel }
        let displayName = model == "deepseek-v4-flash" ? "DeepSeek V4 Flash" : "DeepSeek V4 Pro"

        let modelId = try shell(binary, "--config", configPath, "--print-codex-model")
            .trimmingCharacters(in: .whitespacesAndNewlines)

        var toml = try shell(binary,
            "--config", configPath,
            "--print-codex-config", modelId,
            "--codex-base-url", "http://127.0.0.1:\(port)/v1",
            "--codex-home", codexHome.path)

        // Replace moonbridge branding with the actual model identity
        toml = toml
            .replacingOccurrences(of: "model_provider = \"moonbridge\"",
                                  with: "model_provider = \"\(model)\"")
            .replacingOccurrences(of: "[model_providers.moonbridge]",
                                  with: "[model_providers.\(model)]")
            .replacingOccurrences(of: "name = \"Moon Bridge\"",
                                  with: "name = \"\(displayName)\"")

        // Merge: keep user's original settings (MCP servers, notify, plugins, etc.)
        // Prepend the generated model config, then append original non-model sections
        let backupPath = configDir.appendingPathComponent("config.toml.backup")
        if FileManager.default.fileExists(atPath: backupPath.path),
           let original = try? String(contentsOf: backupPath, encoding: .utf8),
           !original.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            toml = toml + "\n\n# ── Original user settings ──\n" + original
        }

        try FileManager.default.createDirectory(at: codexHome, withIntermediateDirectories: true)
        try toml.write(to: codexHome.appendingPathComponent("config.toml"), atomically: true, encoding: .utf8)
    }

    // MARK: - Helpers

    private func moonBridgePath() -> String {
        if let p = Bundle.main.path(forResource: "moonbridge", ofType: nil) { return p }
        let devPath = URL(fileURLWithPath: #file)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .appendingPathComponent("assets/moonbridge").path
        return devPath
    }

    private func waitForPort() async -> Bool {
        for _ in 0..<50 {
            try? await Task.sleep(nanoseconds: 100_000_000)
            if isPortOpen() { return true }
        }
        return false
    }

    private func isPortOpen() -> Bool {
        let sock = socket(AF_INET, SOCK_STREAM, 0)
        guard sock >= 0 else { return false }
        defer { close(sock) }
        var addr = sockaddr_in()
        addr.sin_family = sa_family_t(AF_INET)
        addr.sin_port = in_port_t(UInt16(port)!).bigEndian
        addr.sin_addr.s_addr = inet_addr("127.0.0.1")
        return withUnsafePointer(to: &addr) {
            $0.withMemoryRebound(to: sockaddr.self, capacity: 1) {
                connect(sock, $0, socklen_t(MemoryLayout<sockaddr_in>.size)) == 0
            }
        }
    }

    @discardableResult
    private func shell(_ cmd: String, _ args: String...) throws -> String {
        let p = Process()
        p.executableURL = URL(fileURLWithPath: cmd)
        p.arguments = args
        let outPipe = Pipe()
        let errPipe = Pipe()
        p.standardOutput = outPipe
        p.standardError = errPipe
        try p.run()
        p.waitUntilExit()
        let data = outPipe.fileHandleForReading.readDataToEndOfFile()
        guard p.terminationStatus == 0 else {
            let errData = errPipe.fileHandleForReading.readDataToEndOfFile()
            let msg = String(data: errData, encoding: .utf8) ?? "unknown error"
            throw NSError(domain: "CodexSwitch", code: Int(p.terminationStatus),
                          userInfo: [NSLocalizedDescriptionKey: msg])
        }
        return String(data: data, encoding: .utf8) ?? ""
    }

    private func restoreCodexConfig() {
        let codexConfig = codexHome.appendingPathComponent("config.toml")
        let backupPath = configDir.appendingPathComponent("config.toml.backup")
        if FileManager.default.fileExists(atPath: backupPath.path) {
            try? FileManager.default.removeItem(at: codexConfig)
            try? FileManager.default.copyItem(at: backupPath, to: codexConfig)
            try? FileManager.default.removeItem(at: backupPath)
        } else {
            try? FileManager.default.removeItem(at: codexConfig)
        }
    }

    func saveSettings() {
        UserDefaults.standard.set(apiKey, forKey: "apiKey")
        UserDefaults.standard.set(selectedModel, forKey: "model")
    }

    func loadSettings() {
        apiKey = UserDefaults.standard.string(forKey: "apiKey") ?? ""
        selectedModel = UserDefaults.standard.string(forKey: "model") ?? "deepseek-v4-pro"
    }
}
