# 海南大学课表同步到 iPhone 日历

这个工具从海南大学正式本科教务系统读取课表，把每一次实际上课生成独立日历事件，并同步到一个名为“海南大学课程”的 iCloud 日历。Mac、iPhone、iPad 和 Apple Watch 使用同一 Apple 账户并开启 iCloud 日历后都会显示。

它不会保存学校账号密码，不会绕过登录或验证码。登录状态只保存在项目的 `.local/browser-profile/`，该目录已被 Git 忽略。

## 已确认的学校接口

- 学期课表：`POST /jsxsd/xskb/xskb_list.do`（HTML）
- 周课表：`GET /jsxsd/framework/mainV_index_loadkb.htmlx`（HTML）
- 调停课：`POST /jsxsd/xskb/loadTtkMxList`（HTML 表格）
- 教学周历：`GET /jsxsd/framework/mainv_index_lzltable.htmlx`

课表字段包括课程名称、教师、周次、节次、校区、教学楼、教室和通知单编号。日期由教学第 1 周星期一、周次和星期换算。当前配置为 `2026-2027-1`，第 1 周星期一是 `2026-08-31`。

## 第一次使用（不会编程也可以）

当前 Mac 已完成安装时，最简单的方式是双击 `outputs/开始同步.command`，它会逐步引导完成下面全部操作。

### 1. 检查 Apple 设备

在 iPhone：

1. 打开“设置”。
2. 点顶部你的姓名。
3. 点“iCloud”。
4. 确认“日历”已开启。

Mac 也必须登录同一 Apple 账户并开启 iCloud 日历。

### 2. 安装

双击 `setup.command`。如果 macOS 阻止打开，按住 Control 点击文件，选“打开”，再确认一次。

### 3. 登录学校

双击 `login.command`。程序会打开一个专用 Chrome 窗口：

1. 你自己输入学校账号、密码和验证码。
2. 看到教务系统首页。
3. 程序检测到登录成功后会自动保存 Session 并关闭，不需要回终端按 Enter。

密码不会进入代码、配置文件或日志。以后 Session 仍有效时不需要重复登录。

### 4. 第一次同步

双击 `sync.command`。第一次写入时，macOS 会询问日历权限，请允许。

如果向导停在第三步：第三步本身不接收回车，它正在等待 macOS 日历权限。先按
`Control-C` 停止旧进程，再双击 `outputs/重试第三步.command`；看到“海南大学课表同步”
权限弹窗时点“允许”。若曾拒绝过，请到“系统设置 → 隐私与安全性 → 日历”重新允许。

同步成功后会看到：

- iCloud 日历中的“海南大学课程”；
- `outputs/hnu-courses.ics` 备份；
- 新增、修改、删除和总事件数量。

### 5. 开启自动同步

确认第一次同步正确后，双击 `install-automation.command`。默认每 60 分钟同步一次。可在 `config.json` 中修改 `syncIntervalMinutes`，最低 15 分钟。

若 Session 过期，自动任务只记录错误，不会清空已有课程。重新双击
`outputs/重新登录自动同步.command`，完成网页登录后程序会自动继续同步。

## iPhone 显示和通知

### 日历

打开“日历”App，点底部“日历”，确认“海南大学课程”已勾选。

### 主屏幕小组件

1. 长按主屏幕空白处。
2. 点“编辑”或左上角加号。
3. 搜索“日历”。
4. 选择“接下来”样式并添加。

### 锁屏

1. 长按锁屏。
2. 点“自定”→“锁定屏幕”。
3. 点时间下方的小组件区域。
4. 添加“日历”的“下一个日程”。

### 通知

前往“设置”→“通知”→“日历”，开启允许通知、锁定屏幕和通知中心。每节课默认有提前 30 分钟和提前 10 分钟两个提醒。

## 配置

`config.json` 中可修改：

- `semesterId`：学年学期；
- `semesterStartDate`：教学第 1 周星期一；
- `timezone`：固定为 `Asia/Shanghai`；
- `alertTimes`：提醒分钟数；
- `calendarName`：iCloud 日历名称；
- `syncIntervalMinutes`：自动同步间隔。

切换学期时只修改 `semesterId`、`semesterStartDate` 和 `maxWeeks`。UID 包含学期标识，新旧学期不会冲突。

## 常用终端命令

```bash
.venv/bin/hnu-calendar login
.venv/bin/hnu-calendar sync
.venv/bin/hnu-calendar sync --ics-only
.venv/bin/hnu-calendar install-automation
.venv/bin/python -m unittest discover -s tests -v
```

## 同步安全规则

- 获取失败、网络错误、登录失效、找不到课表或返回空课表时，不修改旧日历。
- 原始 HTML 和 UID 状态只保存在 `.local/`，权限设为当前用户可读写。
- 只有完整新快照通过解析后才允许删除旧事件。
- 同一事件复用稳定 UID；时间和教室变化更新原事件。
- 每次实际上课都是独立 `VEVENT`，不使用笼统的每周重复规则。
- 只删除工具自己创建、带 `hnu-course://` 标记的事件。

## 当前限制

- 当前学期调停课列表为空，字段结构已接入并用测试数据验证，但真实状态文字需要出现实际记录后再核对一次。
- “无课表课程”没有日期和时间，不会被猜测成日历事件。
- 中午第 12–13、14–15 小节只按学校页面明确给出的完整时间块处理；不猜单独小节时间。
- Mac 必须在开机并联网时才能自动抓取学校课表。
