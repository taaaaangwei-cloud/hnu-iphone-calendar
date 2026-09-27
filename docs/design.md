# 海南大学课程表同步设计

## 已确认数据源

- 正式教务课表：`POST /jsxsd/xskb/xskb_list.do`，返回结构化 HTML。
- 周课表：`GET /jsxsd/framework/mainV_index_loadkb.htmlx`，返回 HTML 片段。
- 调停课：`POST /jsxsd/xskb/loadTtkMxList`，返回 HTML 表格。
- 教学周历：`GET /jsxsd/framework/mainv_index_lzltable.htmlx`。
- 登录：用户在持久化浏览器中正常登录，程序只复用合法 Session。

## 数据流

`authentication -> fetcher -> parser -> semester -> calendar -> sync -> EventKit`

只有完整、非空并通过验证的新快照才能进入同步。任何网络、登录或解析失败都保留上一份有效数据和已有日历。

## 测试边界

- HTML 文本到规范课程块。
- 周次和节次到真实日期时间。
- 规范事件到 RFC 5545 ICS。
- 前后快照到新增、修改和删除集合。
- 登录失效与空课表不会触发日历删除。

