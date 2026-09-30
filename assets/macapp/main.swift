// 全国旅游情报 —— 原生 macOS 外壳（WKWebView）
// 独立 App：自带图标、独立 bundle id、独立窗口，不依赖 Chrome。
// 刷新：页面按钮 → 原生消息通道 travelRefresh → 触发 GitHub Actions 云端采集 → 完成后自动重载。
import Cocoa
import WebKit

let APP_URL = "https://tedvong894.github.io/travel-intel/"
let APP_TITLE = "全国旅游情报"
let REFRESH_SCHEME = "travelintel"

final class AppDelegate: NSObject, NSApplicationDelegate, WKNavigationDelegate, WKUIDelegate, WKScriptMessageHandler {
    var window: NSWindow!
    var webView: WKWebView!
    var refreshing = false

    func applicationDidFinishLaunching(_ note: Notification) {
        buildMenu()

        let rect = NSRect(x: 0, y: 0, width: 1180, height: 840)
        window = NSWindow(contentRect: rect,
                          styleMask: [.titled, .closable, .miniaturizable, .resizable],
                          backing: .buffered, defer: false)
        window.title = APP_TITLE
        window.minSize = NSSize(width: 720, height: 520)
        window.setFrameAutosaveName("TravelIntelMainWindow")
        window.center()

        let cfg = WKWebViewConfiguration()
        cfg.preferences.setValue(true, forKey: "developerExtrasEnabled")
        cfg.userContentController.addUserScript(WKUserScript(
            source: "window.__TRAVEL_NATIVE__ = true;",
            injectionTime: .atDocumentStart, forMainFrameOnly: true))
        cfg.userContentController.add(self, name: "travelRefresh")

        webView = WKWebView(frame: rect, configuration: cfg)
        webView.autoresizingMask = [.width, .height]
        webView.navigationDelegate = self
        webView.uiDelegate = self
        webView.allowsMagnification = true

        window.contentView = webView
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)

        if let url = URL(string: APP_URL) {
            webView.load(URLRequest(url: url))
        }
    }

    private func buildMenu() {
        let mainMenu = NSMenu()

        let appItem = NSMenuItem()
        mainMenu.addItem(appItem)
        let appMenu = NSMenu()
        appMenu.addItem(withTitle: "关于 \(APP_TITLE)", action: #selector(NSApplication.orderFrontStandardAboutPanel(_:)), keyEquivalent: "")
        appMenu.addItem(.separator())
        appMenu.addItem(withTitle: "隐藏 \(APP_TITLE)", action: #selector(NSApplication.hide(_:)), keyEquivalent: "h")
        appMenu.addItem(.separator())
        appMenu.addItem(withTitle: "退出 \(APP_TITLE)", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        appItem.submenu = appMenu

        let editItem = NSMenuItem()
        mainMenu.addItem(editItem)
        let editMenu = NSMenu(title: "编辑")
        editMenu.addItem(withTitle: "撤销", action: Selector(("undo:")), keyEquivalent: "z")
        editMenu.addItem(withTitle: "重做", action: Selector(("redo:")), keyEquivalent: "Z")
        editMenu.addItem(.separator())
        editMenu.addItem(withTitle: "剪切", action: #selector(NSText.cut(_:)), keyEquivalent: "x")
        editMenu.addItem(withTitle: "拷贝", action: #selector(NSText.copy(_:)), keyEquivalent: "c")
        editMenu.addItem(withTitle: "粘贴", action: #selector(NSText.paste(_:)), keyEquivalent: "v")
        editMenu.addItem(withTitle: "全选", action: #selector(NSText.selectAll(_:)), keyEquivalent: "a")
        editItem.submenu = editMenu

        let viewItem = NSMenuItem()
        mainMenu.addItem(viewItem)
        let viewMenu = NSMenu(title: "视图")
        let refreshItem = NSMenuItem(title: "立即刷新（增量采集）",
                                     action: #selector(triggerRefresh), keyEquivalent: "R")
        refreshItem.keyEquivalentModifierMask = [.command, .shift]
        refreshItem.target = self
        viewMenu.addItem(refreshItem)
        viewMenu.addItem(withTitle: "重新载入页面", action: #selector(reloadPage), keyEquivalent: "r")
        viewMenu.addItem(withTitle: "回到首页", action: #selector(goHome), keyEquivalent: "H")
        viewMenu.addItem(.separator())
        viewMenu.addItem(withTitle: "放大", action: #selector(zoomIn), keyEquivalent: "+")
        viewMenu.addItem(withTitle: "缩小", action: #selector(zoomOut), keyEquivalent: "-")
        viewMenu.addItem(withTitle: "实际大小", action: #selector(zoomReset), keyEquivalent: "0")
        viewItem.submenu = viewMenu

        let winItem = NSMenuItem()
        mainMenu.addItem(winItem)
        let winMenu = NSMenu(title: "窗口")
        winMenu.addItem(withTitle: "最小化", action: #selector(NSWindow.performMiniaturize(_:)), keyEquivalent: "m")
        winMenu.addItem(withTitle: "缩放", action: #selector(NSWindow.performZoom(_:)), keyEquivalent: "")
        winItem.submenu = winMenu
        NSApp.windowsMenu = winMenu

        NSApp.mainMenu = mainMenu
    }

    // 拦截自定义协议：travelintel://refresh
    func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction,
                 decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        if let url = navigationAction.request.url, url.scheme == REFRESH_SCHEME {
            decisionHandler(.cancel)
            startRefresh()
            return
        }
        decisionHandler(.allow)
    }

    func webView(_ webView: WKWebView, createWebViewWith configuration: WKWebViewConfiguration,
                 for navigationAction: WKNavigationAction, windowFeatures: WKWindowFeatures) -> WKWebView? {
        if let url = navigationAction.request.url { NSWorkspace.shared.open(url) }
        return nil
    }

    @objc func triggerRefresh() { startRefresh() }

    func userContentController(_ userContentController: WKUserContentController,
                               didReceive message: WKScriptMessage) {
        if message.name == "travelRefresh" { startRefresh() }
    }

    func startRefresh() {
        if refreshing { return }
        refreshing = true
        js("window.__travelRefreshStatus && window.__travelRefreshStatus('正在云端采集新增景点…')")

        guard let script = Bundle.main.path(forResource: "refresh_via_actions", ofType: "sh") else {
            finishFail("找不到刷新脚本（refresh_via_actions.sh 未打包进 App）")
            return
        }

        DispatchQueue.global().async {
            let p = Process()
            p.executableURL = URL(fileURLWithPath: "/bin/bash")
            p.arguments = [script]
            var env = ProcessInfo.processInfo.environment
            env["PATH"] = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:" + (env["PATH"] ?? "")
            p.environment = env

            let pipe = Pipe()
            p.standardOutput = pipe
            p.standardError = pipe
            let handle = pipe.fileHandleForReading
            var buffer = ""
            handle.readabilityHandler = { h in
                let d = h.availableData
                guard !d.isEmpty, let s = String(data: d, encoding: .utf8) else { return }
                buffer += s
                var lines = buffer.components(separatedBy: "\n")
                buffer = lines.removeLast()
                for line in lines where !line.trimmingCharacters(in: .whitespaces).isEmpty {
                    DispatchQueue.main.async { self.handleLine(line.trimmingCharacters(in: .whitespaces)) }
                }
            }

            do {
                try p.run()
            } catch {
                DispatchQueue.main.async { self.finishFail("无法启动刷新脚本：\(error.localizedDescription)") }
                return
            }
            p.waitUntilExit()
            handle.readabilityHandler = nil
            DispatchQueue.main.async {
                if self.refreshing {
                    self.finishFail("刷新未完成（脚本退出码 \(p.terminationStatus)）")
                }
            }
        }
    }

    private func handleLine(_ line: String) {
        if line.hasPrefix("OK ") {
            refreshing = false
            js("window.__travelRefreshDone && window.__travelRefreshDone('✅ 刷新完成，正在载入最新数据…')")
        } else if line.hasPrefix("FAILED ") {
            finishFail(String(line.dropFirst(7)))
        } else {
            js("window.__travelRefreshStatus && window.__travelRefreshStatus(\(jsString(line)))")
        }
    }

    private func finishFail(_ msg: String) {
        refreshing = false
        js("window.__travelRefreshFail && window.__travelRefreshFail(\(jsString("❌ " + msg)))")
        let alert = NSAlert()
        alert.messageText = "刷新失败"
        alert.informativeText = msg
        alert.alertStyle = .warning
        alert.addButton(withTitle: "好")
        alert.runModal()
    }

    private func jsString(_ s: String) -> String {
        let data = (try? JSONSerialization.data(withJSONObject: [s], options: [])) ?? Data()
        var str = String(data: data, encoding: .utf8) ?? "[\"\"]"
        str.removeFirst()
        str.removeLast()
        return str
    }

    private func js(_ code: String) {
        DispatchQueue.main.async { self.webView.evaluateJavaScript(code, completionHandler: nil) }
    }

    @objc func reloadPage() { webView.reload() }
    @objc func goHome() { if let u = URL(string: APP_URL) { webView.load(URLRequest(url: u)) } }
    @objc func zoomIn() { webView.pageZoom = min(webView.pageZoom + 0.1, 3.0) }
    @objc func zoomOut() { webView.pageZoom = max(webView.pageZoom - 0.1, 0.5) }
    @objc func zoomReset() { webView.pageZoom = 1.0 }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.regular)
app.run()
