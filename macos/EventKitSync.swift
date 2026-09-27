import AppKit
import EventKit
import Foundation

struct Input: Decodable {
    let calendarName: String
    let rangeStart: String
    let rangeEnd: String
    let alertTimes: [Int]
    let events: [InputEvent]
}

struct InputEvent: Decodable {
    let uid: String
    let name: String
    let start: String
    let end: String
    let location: String
    let description: String
}

enum SyncFailure: Error, CustomStringConvertible {
    case message(String)

    var description: String {
        switch self { case .message(let value): return value }
    }
}

let markerPrefix = "hnu-course://event/"

func parseDate(_ value: String) throws -> Date {
    let formatter = ISO8601DateFormatter()
    formatter.formatOptions = [.withInternetDateTime, .withColonSeparatorInTimeZone]
    guard let date = formatter.date(from: value) else {
        throw SyncFailure.message("无法解析日程时间：\(value)")
    }
    return date
}

func requestAccess(_ store: EKEventStore) throws {
    switch EKEventStore.authorizationStatus(for: .event) {
    case .fullAccess, .authorized:
        return
    case .denied:
        throw SyncFailure.message("日历权限已被拒绝。请打开系统设置 → 隐私与安全性 → 日历，允许“海南大学课表同步”，然后重新运行第三步。")
    case .restricted:
        throw SyncFailure.message("此 Mac 的日历访问受系统或组织策略限制。")
    case .notDetermined, .writeOnly:
        break
    @unknown default:
        break
    }

    NSApplication.shared.setActivationPolicy(.accessory)
    NSApplication.shared.activate(ignoringOtherApps: true)
    let semaphore = DispatchSemaphore(value: 0)
    var granted = false
    var failure: Error?
    store.requestFullAccessToEvents { value, error in
        granted = value
        failure = error
        semaphore.signal()
    }
    guard semaphore.wait(timeout: .now() + 120) == .success else {
        throw SyncFailure.message("等待日历权限超过 2 分钟。第三步不需要按 Enter；请处理 macOS 权限弹窗后重新运行第三步。")
    }
    if let failure = failure { throw failure }
    if !granted {
        throw SyncFailure.message("没有日历权限。请在系统设置 → 隐私与安全性 → 日历中允许“海南大学课表同步”。")
    }
}

func iCloudSource(_ store: EKEventStore) throws -> EKSource {
    if let source = store.sources.first(where: {
        $0.sourceType == .calDAV && $0.title.lowercased().contains("icloud")
    }) {
        return source
    }
    throw SyncFailure.message("没有找到 iCloud 日历账户。请先在系统设置中开启 iCloud → 日历。")
}

func targetCalendar(_ store: EKEventStore, source: EKSource, name: String) throws -> EKCalendar {
    if let calendar = store.calendars(for: .event).first(where: {
        $0.source.sourceIdentifier == source.sourceIdentifier && $0.title == name
    }) {
        return calendar
    }
    let calendar = EKCalendar(for: .event, eventStore: store)
    calendar.title = name
    calendar.source = source
    try store.saveCalendar(calendar, commit: true)
    return calendar
}

func marker(_ uid: String) -> URL? {
    URL(string: markerPrefix + uid.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed)!)
}

func run() throws {
    guard CommandLine.arguments.count == 2 else {
        throw SyncFailure.message("用法：hnu-eventkit-sync input.json")
    }
    let data = try Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1]))
    let input = try JSONDecoder().decode(Input.self, from: data)
    guard !input.events.isEmpty else {
        throw SyncFailure.message("拒绝同步空课表")
    }

    let rangeStart = try parseDate(input.rangeStart).addingTimeInterval(-86_400)
    let rangeEnd = try parseDate(input.rangeEnd).addingTimeInterval(86_400)
    let store = EKEventStore()
    try requestAccess(store)
    let source = try iCloudSource(store)
    let calendar = try targetCalendar(store, source: source, name: input.calendarName)
    let predicate = store.predicateForEvents(withStart: rangeStart, end: rangeEnd, calendars: [calendar])
    let existing = store.events(matching: predicate)

    var byMarker: [String: EKEvent] = [:]
    var duplicates: [EKEvent] = []
    for event in existing {
        guard let value = event.url?.absoluteString, value.hasPrefix(markerPrefix) else { continue }
        if byMarker[value] == nil { byMarker[value] = event } else { duplicates.append(event) }
    }

    var desiredMarkers = Set<String>()
    let duplicateIDs = Set(duplicates.map { $0.calendarItemIdentifier })
    var created = 0
    var updated = 0
    for item in input.events {
        guard let url = marker(item.uid) else { throw SyncFailure.message("无效 UID：\(item.uid)") }
        let key = url.absoluteString
        desiredMarkers.insert(key)
        let event: EKEvent
        if let found = byMarker[key] {
            event = found
            updated += 1
        } else {
            event = EKEvent(eventStore: store)
            event.calendar = calendar
            created += 1
        }
        event.title = item.name
        event.startDate = try parseDate(item.start)
        event.endDate = try parseDate(item.end)
        event.timeZone = TimeZone(identifier: "Asia/Shanghai")
        event.location = item.location
        event.notes = item.description
        event.url = url
        event.availability = .busy
        event.alarms = input.alertTimes.map { EKAlarm(relativeOffset: -Double($0 * 60)) }
        try store.save(event, span: .thisEvent, commit: false)
    }

    var deleted = 0
    for event in existing {
        guard let value = event.url?.absoluteString, value.hasPrefix(markerPrefix) else { continue }
        if !desiredMarkers.contains(value) || duplicateIDs.contains(event.calendarItemIdentifier) {
            try store.remove(event, span: .thisEvent, commit: false)
            deleted += 1
        }
    }
    try store.commit()
    let result: [String: Any] = ["calendar": input.calendarName, "created": created, "updated": updated, "deleted": deleted]
    let output = try JSONSerialization.data(withJSONObject: result, options: [.sortedKeys])
    print(String(data: output, encoding: .utf8)!)
}

do {
    try run()
} catch {
    FileHandle.standardError.write(("错误：\(error)\n").data(using: .utf8)!)
    exit(1)
}
