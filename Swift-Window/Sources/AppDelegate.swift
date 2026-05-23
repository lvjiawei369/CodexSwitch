import AppKit
import SwiftUI

class AppDelegate: NSObject, NSApplicationDelegate {
    var window: NSWindow!
    var manager = Manager()

    func applicationDidFinishLaunching(_ notification: Notification) {
        createWindow()
    }

    private func createWindow() {
        let hosting = NSHostingController(
            rootView: ContentView().environmentObject(manager)
        )
        // 固定尺寸窗口，不可缩放
        window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 320, height: 290),
            styleMask: [.titled, .closable, .miniaturizable],
            backing: .buffered,
            defer: false
        )
        window.title = "CodexSwitch"
        window.contentViewController = hosting
        window.center()
        // 记住上次位置
        window.setFrameAutosaveName("CodexSwitch.Window")
        // 关闭窗口后不释放，点 Dock 图标可重新打开
        window.isReleasedWhenClosed = false
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    // 点击 Dock 图标时，若窗口已关闭则重新显示
    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        if !flag {
            window.makeKeyAndOrderFront(nil)
            NSApp.activate(ignoringOtherApps: true)
        }
        return true
    }

    // 关闭最后一个窗口时退出 App
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        return true
    }

    func applicationWillTerminate(_ notification: Notification) {
        manager.shutdown()
    }
}

@main
struct CodexSwitchApp {
    static func main() {
        let app = NSApplication.shared
        let delegate = AppDelegate()
        app.delegate = delegate
        app.run()
    }
}
