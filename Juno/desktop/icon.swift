import AppKit
let image = NSImage(size: NSSize(width: 1024, height: 1024))
image.lockFocus()
let rect = NSRect(x: 40, y: 40, width: 944, height: 944)
NSColor(calibratedRed: 0.29, green: 0.20, blue: 0.49, alpha: 1).setFill()
NSBezierPath(roundedRect: rect, xRadius: 210, yRadius: 210).fill()
let attributes: [NSAttributedString.Key: Any] = [.font: NSFont.systemFont(ofSize: 650, weight: .medium), .foregroundColor: NSColor.white]
let letter = NSAttributedString(string: "J", attributes: attributes)
letter.draw(at: NSPoint(x: 300, y: 115))
NSColor(calibratedRed: 0.85, green: 0.75, blue: 1, alpha: 1).setFill()
let star = NSBezierPath(); star.move(to: NSPoint(x: 745, y: 815)); star.line(to: NSPoint(x: 775, y: 740)); star.line(to: NSPoint(x: 850, y: 710)); star.line(to: NSPoint(x: 775, y: 680)); star.line(to: NSPoint(x: 745, y: 605)); star.line(to: NSPoint(x: 715, y: 680)); star.line(to: NSPoint(x: 640, y: 710)); star.line(to: NSPoint(x: 715, y: 740)); star.close(); star.fill()
image.unlockFocus()
let bitmap = NSBitmapImageRep(data: image.tiffRepresentation!)!
try bitmap.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: CommandLine.arguments[1]))
