import AppKit
import SwiftUI

class AppDelegate: NSObject, NSApplicationDelegate {
    var window: NSWindow!
    var manager = Manager()

    func applicationDidFinishLaunching(_ notification: Notification) {
        buildMenuBar()
        createWindow()
    }

    /// 补全标准菜单栏，否则 SwiftUI 文本框无法使用 Cmd+V / 右键粘贴
    private func buildMenuBar() {
        let mainMenu = NSMenu()

        // ── App 菜单 ──────────────────────────────────────────────────
        let appItem = NSMenuItem()
        mainMenu.addItem(appItem)
        let appMenu = NSMenu()
        appItem.submenu = appMenu
        appMenu.addItem(NSMenuItem(title: "退出 CodexSwitch",
                                   action: #selector(NSApplication.terminate(_:)),
                                   keyEquivalent: "q"))

        // ── Edit 菜单（Cut / Copy / Paste / Select All） ───────────────
        let editItem = NSMenuItem()
        mainMenu.addItem(editItem)
        let editMenu = NSMenu(title: "Edit")
        editItem.submenu = editMenu
        editMenu.addItem(NSMenuItem(title: "Cut",
                                    action: #selector(NSText.cut(_:)),
                                    keyEquivalent: "x"))
        editMenu.addItem(NSMenuItem(title: "Copy",
                                    action: #selector(NSText.copy(_:)),
                                    keyEquivalent: "c"))
        editMenu.addItem(NSMenuItem(title: "Paste",
                                    action: #selector(NSText.paste(_:)),
                                    keyEquivalent: "v"))
        editMenu.addItem(NSMenuItem(title: "Select All",
                                    action: #selector(NSText.selectAll(_:)),
                                    keyEquivalent: "a"))

        NSApp.mainMenu = mainMenu
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
