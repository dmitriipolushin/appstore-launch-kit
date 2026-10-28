import Foundation
import Vision
import AppKit
let dir = CommandLine.arguments[1]
var out: [String: String] = [:]
let files = try FileManager.default.contentsOfDirectory(atPath: dir).filter { $0.hasSuffix(".jpg") }.sorted()
for f in files {
    guard let img = NSImage(contentsOfFile: dir + "/" + f),
          let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { continue }
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    req.recognitionLanguages = ["en-US", "ja-JP", "zh-Hans", "ko-KR", "fr-FR", "de-DE", "es-ES"]
    req.usesLanguageCorrection = true
    try? VNImageRequestHandler(cgImage: cg, options: [:]).perform([req])
    // sort by size (bigger text = headline first)
    let obs = (req.results ?? []).sorted { $0.boundingBox.height > $1.boundingBox.height }
    out[f] = obs.compactMap { $0.topCandidates(1).first?.string }.prefix(12).joined(separator: " | ")
}
let data = try JSONSerialization.data(withJSONObject: out, options: [.prettyPrinted])
FileManager.default.createFile(atPath: CommandLine.arguments[2], contents: data)
print(out.count)
