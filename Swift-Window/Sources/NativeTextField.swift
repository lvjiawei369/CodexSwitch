import AppKit
import SwiftUI

struct NativeTextField: NSViewRepresentable {
    @Binding var text: String
    var placeholder: String = ""
    var isSecure: Bool = false
    var isEnabled: Bool = true

    func makeCoordinator() -> Coordinator { Coordinator(self) }

    func makeNSView(context: Context) -> NSTextField {
        let field = isSecure ? NSSecureTextField() : NSTextField()
        field.placeholderString = placeholder
        field.delegate = context.coordinator
        field.bezelStyle = .roundedBezel
        field.isBordered = true
        field.isEditable = true
        field.isSelectable = true
        field.focusRingType = .default
        return field
    }

    func updateNSView(_ nsView: NSTextField, context: Context) {
        if nsView.stringValue != text {
            nsView.stringValue = text
        }
        nsView.isEnabled = isEnabled
        context.coordinator.parent = self
    }

    class Coordinator: NSObject, NSTextFieldDelegate {
        var parent: NativeTextField
        init(_ parent: NativeTextField) { self.parent = parent }

        func controlTextDidChange(_ obj: Notification) {
            if let field = obj.object as? NSTextField {
                parent.text = field.stringValue
            }
        }
    }
}
