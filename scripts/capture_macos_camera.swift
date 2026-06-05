import AppKit
import AVFoundation
import CoreImage
import Foundation

final class FrameCaptureDelegate: NSObject, AVCaptureVideoDataOutputSampleBufferDelegate {
    let outputURL: URL
    let semaphore: DispatchSemaphore
    var failure: Error?
    private let context = CIContext()
    private var didCapture = false

    init(outputURL: URL, semaphore: DispatchSemaphore) {
        self.outputURL = outputURL
        self.semaphore = semaphore
    }

    func captureOutput(
        _ output: AVCaptureOutput,
        didOutput sampleBuffer: CMSampleBuffer,
        from connection: AVCaptureConnection
    ) {
        guard !didCapture else { return }
        didCapture = true
        defer { semaphore.signal() }

        guard let imageBuffer = CMSampleBufferGetImageBuffer(sampleBuffer) else {
            failure = NSError(
                domain: "McpCameraWatch",
                code: 1,
                userInfo: [NSLocalizedDescriptionKey: "Camera did not return a video frame."]
            )
            return
        }

        let image = CIImage(cvImageBuffer: imageBuffer)
        guard let cgImage = context.createCGImage(image, from: image.extent) else {
            failure = NSError(
                domain: "McpCameraWatch",
                code: 2,
                userInfo: [NSLocalizedDescriptionKey: "Could not convert the camera frame."]
            )
            return
        }

        let bitmap = NSBitmapImageRep(cgImage: cgImage)
        guard let jpeg = bitmap.representation(using: .jpeg, properties: [.compressionFactor: 0.9]) else {
            failure = NSError(
                domain: "McpCameraWatch",
                code: 3,
                userInfo: [NSLocalizedDescriptionKey: "Could not encode the camera frame as JPEG."]
            )
            return
        }

        do {
            try jpeg.write(to: outputURL)
        } catch {
            failure = error
        }
    }
}

func fail(_ message: String) -> Never {
    FileHandle.standardError.write(Data("ERROR: \(message)\n".utf8))
    exit(1)
}

func cameraDevices() -> [AVCaptureDevice] {
    AVCaptureDevice.DiscoverySession(
        deviceTypes: [.builtInWideAngleCamera, .external, .continuityCamera],
        mediaType: .video,
        position: .unspecified
    ).devices
}

func waitForCameraPermission() -> Bool {
    switch AVCaptureDevice.authorizationStatus(for: .video) {
    case .authorized:
        return true
    case .notDetermined:
        let semaphore = DispatchSemaphore(value: 0)
        var granted = false
        AVCaptureDevice.requestAccess(for: .video) { result in
            granted = result
            semaphore.signal()
        }
        _ = semaphore.wait(timeout: .now() + 60)
        return granted
    default:
        return false
    }
}

var outputPath: String?
var requestedDeviceName: String?
var listOnly = false
var index = 1
let arguments = CommandLine.arguments

while index < arguments.count {
    switch arguments[index] {
    case "--output":
        index += 1
        guard index < arguments.count else { fail("--output requires a path.") }
        outputPath = arguments[index]
    case "--device":
        index += 1
        guard index < arguments.count else { fail("--device requires a camera name.") }
        requestedDeviceName = arguments[index]
    case "--list":
        listOnly = true
    default:
        fail("Unknown argument: \(arguments[index])")
    }
    index += 1
}

let devices = cameraDevices()
if listOnly {
    for device in devices {
        print(device.localizedName)
    }
    exit(0)
}

guard waitForCameraPermission() else {
    fail("Camera access was denied. Allow camera access for Codex or your terminal in System Settings > Privacy & Security > Camera.")
}

guard let outputPath else { fail("--output is required.") }

let selectedDevice: AVCaptureDevice?
if let requestedDeviceName {
    selectedDevice = devices.first {
        $0.localizedName.localizedCaseInsensitiveCompare(requestedDeviceName) == .orderedSame
    } ?? devices.first {
        $0.localizedName.localizedCaseInsensitiveContains(requestedDeviceName)
    }
} else {
    selectedDevice = AVCaptureDevice.default(for: .video)
}

guard let selectedDevice else {
    let available = devices.map(\.localizedName).joined(separator: ", ")
    fail("Camera was not found. Available cameras: \(available)")
}

let session = AVCaptureSession()
let videoOutput = AVCaptureVideoDataOutput()

do {
    let input = try AVCaptureDeviceInput(device: selectedDevice)
    guard session.canAddInput(input) else { fail("Could not add camera input.") }
    session.addInput(input)
} catch {
    fail("Could not open camera \(selectedDevice.localizedName): \(error.localizedDescription)")
}

guard session.canAddOutput(videoOutput) else { fail("Could not add camera video output.") }
session.addOutput(videoOutput)

let semaphore = DispatchSemaphore(value: 0)
let delegate = FrameCaptureDelegate(
    outputURL: URL(fileURLWithPath: outputPath),
    semaphore: semaphore
)
let captureQueue = DispatchQueue(label: "com.villocitylabs.mcp-camera-watch.capture")
videoOutput.alwaysDiscardsLateVideoFrames = true
videoOutput.setSampleBufferDelegate(delegate, queue: captureQueue)

session.startRunning()

if semaphore.wait(timeout: .now() + 20) == .timedOut {
    session.stopRunning()
    fail("Timed out waiting for a camera frame.")
}

session.stopRunning()
if let failure = delegate.failure {
    fail(failure.localizedDescription)
}

print(outputPath)
