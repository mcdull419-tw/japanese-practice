// PWA 圖示產生器。執行一次即可，產出的 PNG 納入版控（部署時要跟著網站走）。
// 用法：swift tools/make_icons.swift
import AppKit

for size in [192, 512] {
    let s = CGFloat(size)
    let img = NSImage(size: NSSize(width: s, height: s))
    img.lockFocus()
    NSColor(red: 0.176, green: 0.424, blue: 0.875, alpha: 1).setFill()
    NSRect(x: 0, y: 0, width: s, height: s).fill()
    let attrs: [NSAttributedString.Key: Any] = [
        .font: NSFont.systemFont(ofSize: s * 0.6, weight: .bold),
        .foregroundColor: NSColor.white,
    ]
    let text = "日" as NSString
    let bounds = text.size(withAttributes: attrs)
    text.draw(at: NSPoint(x: (s - bounds.width) / 2, y: (s - bounds.height) / 2),
              withAttributes: attrs)
    img.unlockFocus()
    guard let tiff = img.tiffRepresentation, let rep = NSBitmapImageRep(data: tiff),
          let png = rep.representation(using: .png, properties: [:]) else { continue }
    try? png.write(to: URL(fileURLWithPath: "icon-\(size).png"))
    print("icon-\(size).png")
}
