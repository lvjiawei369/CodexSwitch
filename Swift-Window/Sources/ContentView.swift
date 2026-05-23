import SwiftUI

struct ContentView: View {
    @EnvironmentObject var manager: Manager
    @State private var showKey = false

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            // Header
            HStack(spacing: 6) {
                Image(systemName: "bolt.fill")
                    .foregroundStyle(.yellow)
                Text("CodexSwitch")
                    .font(.headline)
            }

            Divider()

            // API Key
            VStack(alignment: .leading, spacing: 4) {
                Text("DeepSeek API Key")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                HStack(spacing: 6) {
                    NativeTextField(
                        text: $manager.apiKey,
                        placeholder: "sk-...",
                        isSecure: !showKey,
                        isEnabled: !manager.isEnabled && !manager.isLoading
                    )
                    .frame(height: 22)
                    .id(showKey)

                    Button {
                        showKey.toggle()
                    } label: {
                        Image(systemName: showKey ? "eye.slash" : "eye")
                            .foregroundStyle(.secondary)
                            .frame(width: 20)
                    }
                    .buttonStyle(.plain)
                }
            }

            // Model picker
            VStack(alignment: .leading, spacing: 4) {
                Text("Model")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Picker("", selection: $manager.selectedModel) {
                    Text("DeepSeek V4 Pro").tag("deepseek-v4-pro")
                    Text("DeepSeek V4 Flash").tag("deepseek-v4-flash")
                }
                .pickerStyle(.menu)
                .labelsHidden()
                .disabled(manager.isEnabled || manager.isLoading)
            }

            Divider()

            // Toggle row
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text("DeepSeek")
                        .font(.body)
                    HStack(spacing: 4) {
                        if manager.isEnabled && !manager.isLoading {
                            Circle()
                                .fill(.green)
                                .frame(width: 6, height: 6)
                        }
                        Text(manager.statusText)
                            .font(.caption2)
                            .foregroundStyle(manager.isEnabled ? .green : .secondary)
                    }
                }

                Spacer()

                if manager.isLoading {
                    ProgressView()
                        .scaleEffect(0.7)
                        .padding(.trailing, 4)
                }

                Toggle("", isOn: Binding(
                    get: { manager.isEnabled },
                    set: { newVal in
                        manager.isEnabled = newVal
                        manager.toggle()
                    }
                ))
                .labelsHidden()
                .toggleStyle(.switch)
                .disabled(manager.isLoading || (manager.apiKey.trimmingCharacters(in: .whitespaces).isEmpty && !manager.isEnabled))
            }
        }
        .padding(20)
        .frame(width: 320)
    }
}
