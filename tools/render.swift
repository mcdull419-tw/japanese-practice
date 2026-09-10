import Foundation
import PDFKit
import AppKit

let a = CommandLine.arguments
guard a.count >= 3, let doc = PDFDocument(url: URL(fileURLWithPath: a[1])) else {
    FileHandle.standardError.write("usage: render.swift <pdf> <outdir> [scale] [first] [last]\n".data(using:.utf8)!)
    exit(1)
}
let outDir = a[2]
let scale = a.count > 3 ? CGFloat(Double(a[3]) ?? 2.0) : 2.0
let first = a.count > 4 ? (Int(a[4]) ?? 1) : 1
let last  = a.count > 5 ? (Int(a[5]) ?? doc.pageCount) : doc.pageCount
try? FileManager.default.createDirectory(atPath: outDir, withIntermediateDirectories: true)
for i in (first-1)..<min(last, doc.pageCount) {
    guard let page = doc.page(at: i) else { continue }
    let r = page.bounds(for: .mediaBox)
    let size = NSSize(width: r.width*scale, height: r.height*scale)
    let img = NSImage(size: size)
    img.lockFocus()
    NSColor.white.setFill()
    NSRect(origin: .zero, size: size).fill()
    let ctx = NSGraphicsContext.current!.cgContext
    ctx.scaleBy(x: scale, y: scale)
    ctx.translateBy(x: -r.origin.x, y: -r.origin.y)
    page.draw(with: .mediaBox, to: ctx)
    img.unlockFocus()
    guard let tiff = img.tiffRepresentation, let rep = NSBitmapImageRep(data: tiff),
          let png = rep.representation(using: .png, properties: [:]) else { continue }
    let path = "\(outDir)/p\(String(format: "%02d", i+1)).png"
    try? png.write(to: URL(fileURLWithPath: path))
    print(path)
}
